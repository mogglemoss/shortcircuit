# app.py

from enum import Enum
import json
import os
import sys
import time
from functools import partial
from typing import Dict, List, TypedDict, Union

from appdirs import AppDirs
from PySide6 import QtCore, QtGui, QtWidgets
import qdarktheme

from . import __appname__, __appslug__, __date__ as last_update, __version__
import shortcircuit.resources
from .model.esi_processor import ESIProcessor
from .model.evedb import EveDb, Restrictions, SpaceType, WormholeSize
from .model.logger import Logger
from .model.navigation import Navigation
from .model.navprocessor import NavProcessor
from .model.versioncheck import VersionCheck


class StateEVEConnection(TypedDict):
  connected: bool
  char_name: Union[str, None]
  error: Union[str, None]


class StateEVEScout(TypedDict):
  connections: int
  enabled: bool
  error: Union[str, None]


class StateTripwire(TypedDict):
  connections: int
  error: Union[str, None]


class StatePathfinder(TypedDict):
  connections: int
  enabled: bool
  error: Union[str, None]


class StateWanderer(TypedDict):
  connections: int
  enabled: bool
  error: Union[str, None]


class TripwireDialog(QtWidgets.QDialog):
  """
  Tripwire Configuration Window
  """

  def __init__(
    self,
    trip_url,
    trip_user,
    trip_pass,
    proxy,
    evescout_enabled,
    auto_refresh_enabled,
    auto_refresh_interval,
    clear_cookies_callback,
    test_connection_callback,
    test_pf_callback,
    pf_url,
    pf_token,
    pf_enabled,
    test_wanderer_callback,
    wanderer_url,
    wanderer_map_id,
    wanderer_token,
    wanderer_enabled,
    parent=None,
  ):
    super().__init__(parent)
    self.setWindowTitle("Configuration")
    self.setMinimumWidth(400)

    main_layout = QtWidgets.QVBoxLayout(self)

    # Tabs
    self.tabs = QtWidgets.QTabWidget()
    main_layout.addWidget(self.tabs)

    # --- Tripwire Tab ---
    self.tab_tripwire = QtWidgets.QWidget()
    self.tabs.addTab(self.tab_tripwire, "Tripwire")
    trip_layout = QtWidgets.QVBoxLayout(self.tab_tripwire)

    # Form
    form_layout = QtWidgets.QFormLayout()

    self.lineEdit_url = QtWidgets.QLineEdit(trip_url)
    form_layout.addRow("URL:", self.lineEdit_url)

    self.lineEdit_user = QtWidgets.QLineEdit(trip_user)
    form_layout.addRow("Username:", self.lineEdit_user)

    self.lineEdit_pass = QtWidgets.QLineEdit(trip_pass)
    self.lineEdit_pass.setEchoMode(QtWidgets.QLineEdit.Password)
    form_layout.addRow("Password:", self.lineEdit_pass)

    self.lineEdit_proxy = QtWidgets.QLineEdit(proxy)
    self.lineEdit_proxy.setPlaceholderText("http://user:pass@host:port")
    form_layout.addRow("Proxy:", self.lineEdit_proxy)

    self.pushButton_test = QtWidgets.QPushButton("Test Connection")
    self.pushButton_test.clicked.connect(lambda: test_connection_callback(
        self.lineEdit_url.text(),
        self.lineEdit_user.text(),
        self.lineEdit_pass.text(),
        self.lineEdit_proxy.text()
    ))
    form_layout.addRow("", self.pushButton_test)

    # Auto-refresh configuration
    refresh_widget = QtWidgets.QWidget()
    refresh_layout = QtWidgets.QHBoxLayout(refresh_widget)
    refresh_layout.setContentsMargins(0, 0, 0, 0)

    self.checkBox_auto_refresh = QtWidgets.QCheckBox("Enable")
    self.checkBox_auto_refresh.setChecked(auto_refresh_enabled)
    refresh_layout.addWidget(self.checkBox_auto_refresh)

    self.spinBox_interval = QtWidgets.QSpinBox()
    self.spinBox_interval.setRange(10, 600)
    self.spinBox_interval.setValue(auto_refresh_interval)
    self.spinBox_interval.setSuffix(" s")
    refresh_layout.addWidget(self.spinBox_interval)
    form_layout.addRow("Auto-refresh:", refresh_widget)

    # Clear Cookies
    self.pushButton_clear_cookies = QtWidgets.QPushButton("Clear Cookies")
    self.pushButton_clear_cookies.clicked.connect(clear_cookies_callback)
    form_layout.addRow("Session:", self.pushButton_clear_cookies)

    trip_layout.addLayout(form_layout)

    # Eve-Scout
    self.checkBox_evescout = QtWidgets.QCheckBox("Enable Eve-Scout (Thera connections)")
    self.checkBox_evescout.setChecked(evescout_enabled)
    trip_layout.addWidget(self.checkBox_evescout)

    # Logo / Link
    self.label_evescout_logo = QtWidgets.QLabel("Eve-Scout")
    self.label_evescout_logo.setAlignment(QtCore.Qt.AlignCenter)
    self.label_evescout_logo.setCursor(QtCore.Qt.PointingHandCursor)
    self.label_evescout_logo.mouseReleaseEvent = TripwireDialog.logo_click
    trip_layout.addWidget(self.label_evescout_logo)
    trip_layout.addStretch()

    # --- Pathfinder Tab ---
    self.tab_pathfinder = QtWidgets.QWidget()
    self.tabs.addTab(self.tab_pathfinder, "Pathfinder")
    pf_layout = QtWidgets.QVBoxLayout(self.tab_pathfinder)

    pf_form = QtWidgets.QFormLayout()
    self.lineEdit_pf_url = QtWidgets.QLineEdit(pf_url)
    self.lineEdit_pf_url.setPlaceholderText("https://pathfinder.your-corp.com/")
    pf_form.addRow("URL:", self.lineEdit_pf_url)

    self.lineEdit_pf_token = QtWidgets.QLineEdit(pf_token)
    self.lineEdit_pf_token.setEchoMode(QtWidgets.QLineEdit.Password)
    pf_form.addRow("API Token:", self.lineEdit_pf_token)

    self.pushButton_pf_test = QtWidgets.QPushButton("Test Connection")
    self.pushButton_pf_test.clicked.connect(lambda: test_pf_callback(
        self.lineEdit_pf_url.text(),
        self.lineEdit_pf_token.text()
    ))
    pf_form.addRow("", self.pushButton_pf_test)
    pf_layout.addLayout(pf_form)

    self.checkBox_pf_enabled = QtWidgets.QCheckBox("Enable Pathfinder")
    self.checkBox_pf_enabled.setChecked(pf_enabled)
    pf_layout.addWidget(self.checkBox_pf_enabled)
    pf_layout.addStretch()

    # --- Wanderer Tab ---
    self.tab_wanderer = QtWidgets.QWidget()
    self.tabs.addTab(self.tab_wanderer, "Wanderer")
    wanderer_layout = QtWidgets.QVBoxLayout(self.tab_wanderer)

    wanderer_form = QtWidgets.QFormLayout()
    self.lineEdit_wanderer_url = QtWidgets.QLineEdit(wanderer_url)
    self.lineEdit_wanderer_url.setPlaceholderText("https://wanderer.example.com")
    wanderer_form.addRow("URL:", self.lineEdit_wanderer_url)

    self.lineEdit_wanderer_map_id = QtWidgets.QLineEdit(wanderer_map_id)
    self.lineEdit_wanderer_map_id.setPlaceholderText("map-slug")
    wanderer_form.addRow("Map ID:", self.lineEdit_wanderer_map_id)

    self.lineEdit_wanderer_token = QtWidgets.QLineEdit(wanderer_token)
    self.lineEdit_wanderer_token.setEchoMode(QtWidgets.QLineEdit.Password)
    wanderer_form.addRow("Token:", self.lineEdit_wanderer_token)

    self.pushButton_wanderer_test = QtWidgets.QPushButton("Test Connection")
    self.pushButton_wanderer_test.clicked.connect(lambda: test_wanderer_callback(
        self.lineEdit_wanderer_url.text(),
        self.lineEdit_wanderer_map_id.text(),
        self.lineEdit_wanderer_token.text()
    ))
    wanderer_form.addRow("", self.pushButton_wanderer_test)
    wanderer_layout.addLayout(wanderer_form)

    self.checkBox_wanderer_enabled = QtWidgets.QCheckBox("Enable Wanderer")
    self.checkBox_wanderer_enabled.setChecked(wanderer_enabled)
    wanderer_layout.addWidget(self.checkBox_wanderer_enabled)
    wanderer_layout.addStretch()

    # Buttons
    button_box = QtWidgets.QDialogButtonBox(
      QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
    )
    button_box.accepted.connect(self.accept)
    button_box.rejected.connect(self.reject)
    main_layout.addWidget(button_box)

  @staticmethod
  def logo_click(event):
    event.accept()
    QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://www.eve-scout.com/"))


class AboutDialog(QtWidgets.QDialog):
  """
  About Dialog
  """

  def __init__(self, check_updates_callback=None, parent=None):
    super().__init__(parent)
    self.setWindowTitle("About Short Circuit")
    self.setFixedSize(400, 380)

    layout = QtWidgets.QVBoxLayout(self)

    # Header
    header = QtWidgets.QHBoxLayout()

    self.label_title = QtWidgets.QLabel()
    font = self.label_title.font()
    font.setPointSize(12)
    font.setBold(True)
    self.label_title.setFont(font)
    self.label_title.setAlignment(QtCore.Qt.AlignCenter)
    self.label_title.setText(
      '{} v{} ({})'.format(
        __appname__,
        __version__,
        last_update,
      )
    )
    header.addWidget(self.label_title)

    self.label_icon = QtWidgets.QLabel()
    self.label_icon.setPixmap(QtGui.QPixmap(":/images/app_icon_small.png"))
    self.label_icon.setCursor(QtCore.Qt.PointingHandCursor)
    self.label_icon.mouseReleaseEvent = AboutDialog.icon_click
    header.addWidget(self.label_icon)

    layout.addLayout(header)

    # Text
    self.label_2 = QtWidgets.QLabel()
    self.label_2.setWordWrap(True)
    self.label_2.setText(
      "<html><head/><body>"
      "<p>Short Circuit is an open-source application able to find the shortest path between solar systems (wormholes included) using the Eve SDE and wormhole mapping tools such as Tripwire. Short Circuit can run on all platforms where Python and PySide are supported. </p>"
      "<p>Original author – Valtyr Farshield. </p>"
      "<p><span style=\" font-weight:600;\">Maintainer list</span></p>"
      "<ul style=\"margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;\">"
      "<li style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Rustam @SecondFry Gubaydullin (Lenai Chelien).</li></ul>"
      "<p><span style=\" font-weight:600;\">Credits</span></p>"
      "<ul style=\"margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;\">"
      "<li style=\" margin-top:12px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Daimian Mercer (Tripwire). </li>"
      "<li style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Dreae (PyCrest). </li>"
      "<li style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">pyfa-org (PyFa). </li>"
      "<li style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">EvE-Scout. </li>"
      "<li style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Sharps. </li>"
      "<li style=\" margin-top:0px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">choo t. </li>"
      "</ul></body></html>"
    )
    self.label_2.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
    layout.addWidget(self.label_2)

    layout.addStretch()

    # Button
    btn_layout = QtWidgets.QHBoxLayout()
    
    self.pushButton_logs = QtWidgets.QPushButton("Open Logs")
    self.pushButton_logs.clicked.connect(self.open_logs)
    btn_layout.addWidget(self.pushButton_logs)

    self.pushButton_debug = QtWidgets.QPushButton("Debug Colors")
    self.pushButton_debug.clicked.connect(self.debug_colors)
    btn_layout.addWidget(self.pushButton_debug)

    if check_updates_callback:
      self.pushButton_updates = QtWidgets.QPushButton("Check Updates")
      self.pushButton_updates.clicked.connect(check_updates_callback)
      btn_layout.addWidget(self.pushButton_updates)

    btn_layout.addStretch()
    self.pushButton_o7 = QtWidgets.QPushButton("  Fly safe o7  ")
    self.pushButton_o7.clicked.connect(self.close)
    btn_layout.addWidget(self.pushButton_o7)
    layout.addLayout(btn_layout)

  @staticmethod
  def icon_click(event):
    event.accept()
    QtGui.QDesktopServices.openUrl(
      QtCore.QUrl("https://github.com/secondfry/shortcircuit")
    )

  def open_logs(self):
    app_dirs = AppDirs(__appslug__, "secondfry", version=__version__)
    log_dir = app_dirs.user_log_dir
    if os.path.exists(log_dir):
      QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(log_dir))

  def debug_colors(self):
    if self.parent() and hasattr(self.parent(), 'add_data_to_table'):
      mock_route = [
        {'id': 1, 'name': 'Jita', 'class': 'HS', 'security': 0.9, 'path_action': 'Start', 'path_info': ''},
        {'id': 2, 'name': 'Tama', 'class': 'LS', 'security': 0.3, 'path_action': 'Jump gate', 'path_info': ''},
        {'id': 3, 'name': 'H-PA29', 'class': 'NS', 'security': -0.1, 'path_action': 'Jump gate', 'path_info': ''},
        {'id': 4, 'name': 'J123456', 'class': 'C3', 'security': -1.0, 'path_action': 'Jump wormhole', 'path_info': 'Large'},
        {'id': 5, 'name': 'Thera', 'class': 'WH', 'security': -1.0, 'path_action': 'Jump wormhole', 'path_info': 'XL'},
      ]
      self.parent().add_data_to_table(mock_route)
      if hasattr(self.parent(), 'label_status'):
        self.parent().label_status.setText("DEBUG COLORS APPLIED")
      self.close()

class MessageType(Enum):
  INFO = 0
  ERROR = 1
  OK = 2


class RouteWorker(QtCore.QObject):
  finished = QtCore.Signal(list, str)

  def __init__(self, nav):
    super().__init__()
    self.nav = nav

  @QtCore.Slot(int, int)
  def process(self, source_id, dest_id):
    try:
      result = self.nav.route(source_id, dest_id)
      self.finished.emit(result[0], result[1])
    except Exception as e:
      Logger.error("Routing exception: {}".format(e))
      self.finished.emit([], "")


class MainWindow(QtWidgets.QMainWindow):
  """
  Main Window GUI
  """

  @property
  def route_source(self) -> str:
    text_input = self.lineEdit_source.text().strip()
    eve_db = EveDb()
    ret = eve_db.normalize_name(text_input)

    if not ret:
      ret = 'Jita'

    return ret

  start_route_calculation = QtCore.Signal(int, int)
  start_version_check = QtCore.Signal()

  def __init__(self, parent=None):
    super().__init__(parent)
    self.settings = QtCore.QSettings(
      QtCore.QSettings.IniFormat,
      QtCore.QSettings.UserScope,
      __appname__,
    )

    self.tripwire_url = None
    self.tripwire_user = None
    self.tripwire_pass = None
    self.global_proxy = None
    self.auto_refresh_enabled = False
    self.auto_refresh_interval = 30

    # Pathfinder settings
    self.pathfinder_url = None
    self.pathfinder_token = None
    self.pathfinder_enabled = False

    # Wanderer settings
    self.wanderer_url = None
    self.wanderer_map_id = None
    self.wanderer_token = None
    self.wanderer_enabled = False

    self.state_eve_connection = StateEVEConnection({
      "connected": False, "char_name": None, "error": None
    })
    self.state_evescout = StateEVEScout({
      "connections": 0, "enabled": False, "error": None
    })
    self.state_tripwire = StateTripwire({"connections": 0, "error": None})
    self.state_pathfinder = StatePathfinder({
      "connections": 0, "enabled": False, "error": None
    })
    self.state_wanderer = StateWanderer({
      "connections": 0, "enabled": False, "error": None
    })
    
    self.auto_refresh_timer = QtCore.QTimer(self)
    self.auto_refresh_timer.setInterval(self.auto_refresh_interval * 1000)
    self.auto_refresh_timer.timeout.connect(self.auto_refresh_triggered)

    # Create UI Elements (replaces setupUi)
    self._create_ui_elements()

    # Table configuration
    self.tableWidget_path.setColumnCount(5)
    self.tableWidget_path.setHorizontalHeaderLabels([
      "System",
      "Cls",
      "Sec",
      "Instructions",
      "Additional information",
    ])
    header: QtWidgets.QHeaderView = self.tableWidget_path.horizontalHeader()
    header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
    self.tableWidget_path.horizontalHeader().setStretchLastSection(True)

    # Read resources
    self.eve_db = EveDb()
    self.nav = Navigation(self, self.eve_db)

    # Apply Sidebar Layout
    self._setup_ui_layout()

    # Additional GUI setup
    self.additional_gui_setup()

    # Read stored settings
    self.read_settings()

    self.status_tripwire = QtWidgets.QLabel()
    self.status_tripwire.setContentsMargins(5, 0, 5, 0)
    self.statusBar().addPermanentWidget(self.status_tripwire, 0)
    self._status_tripwire_update()

    self.status_evescout = QtWidgets.QLabel()
    self.status_evescout.setContentsMargins(5, 0, 5, 0)
    self.statusBar().addPermanentWidget(self.status_evescout, 0)
    self._status_evescout_update()

    self.status_pathfinder = QtWidgets.QLabel()
    self.status_pathfinder.setContentsMargins(5, 0, 5, 0)
    self.statusBar().addPermanentWidget(self.status_pathfinder, 0)
    self._status_pathfinder_update()

    self.status_wanderer = QtWidgets.QLabel()
    self.status_wanderer.setContentsMargins(5, 0, 5, 0)
    self.statusBar().addPermanentWidget(self.status_wanderer, 0)
    self._status_wanderer_update()

    self.status_eve_connection = QtWidgets.QLabel()
    self.status_eve_connection.setContentsMargins(5, 0, 5, 0)
    self.statusBar().addPermanentWidget(self.status_eve_connection, 0)
    self._status_eve_connection_update()

    # Icons
    self.icon_wormhole = QtGui.QIcon(":/images/wh_icon.png")

    # Thread initial config
    Logger.register_thread(QtCore.QThread.currentThread(), 'main')

    # NavProcessor thread
    self.worker_thread = QtCore.QThread()
    Logger.register_thread(self.worker_thread, 'worker_thread / NavProcessor')
    self.nav_processor = NavProcessor(self.nav)
    self.nav_processor.moveToThread(self.worker_thread)
    self.nav_processor.finished.connect(self.worker_thread_done)
    # noinspection PyUnresolvedReferences
    self.worker_thread.started.connect(self.nav_processor.process)

    # Version check thread
    self.version_thread = QtCore.QThread()
    Logger.register_thread(self.version_thread, 'version_thread / VersionCheck')
    self.version_check = VersionCheck()
    self.version_check.moveToThread(self.version_thread)
    self.version_check.finished.connect(self.version_check_done)
    # noinspection PyUnresolvedReferences
    self.version_thread.started.connect(self.version_check.process)
    self.start_version_check.connect(self.version_check.process)

    # Route thread
    self.route_thread = QtCore.QThread()
    Logger.register_thread(self.route_thread, 'route_thread')
    self.route_worker = RouteWorker(self.nav)
    self.route_worker.moveToThread(self.route_thread)
    self.route_worker.finished.connect(self.route_result_handler)
    self.start_route_calculation.connect(self.route_worker.process)
    self.route_thread.start()

    # ESI
    self.eve_connected = False
    self.esip = ESIProcessor()
    self.esip.login_response.connect(self.login_handler)
    self.esip.logout_response.connect(self.logout_handler)
    self.esip.location_response.connect(self.location_handler)
    self.esip.destination_response.connect(self.destination_handler)

    # Start version check
    self.version_thread.start()

    # Apply custom theme
    self._apply_styles()

  def _create_ui_elements(self):
    """
    Instantiates all UI widgets programmatically, replacing the old .ui file.
    """
    # Navigation
    self.pushButton_eve_login = QtWidgets.QPushButton("Log in with EvE")
    self.pushButton_player_location = QtWidgets.QPushButton("Get player location")
    self.pushButton_player_location.setEnabled(False)

    self.lineEdit_set_dest = QtWidgets.QLineEdit()
    self.lineEdit_set_dest.setPlaceholderText("System name")
    self.pushButton_set_dest = QtWidgets.QPushButton("Set destination")
    self.pushButton_set_dest.setEnabled(False)

    self.lineEdit_source = QtWidgets.QLineEdit()
    self.lineEdit_source.setPlaceholderText("Source system")
    self.lineEdit_destination = QtWidgets.QLineEdit()
    self.lineEdit_destination.setPlaceholderText("Destination system")

    self.pushButton_find_path = QtWidgets.QPushButton("Find path")
    self.pushButton_reset = QtWidgets.QPushButton("Reset chain")

    # Tripwire
    self.pushButton_trip_config = QtWidgets.QPushButton("Tripwire")
    self.pushButton_trip_get = QtWidgets.QPushButton("Get Chain")
    self.pushButton_trip_get.setEnabled(False)

    # Restrictions
    self.comboBox_size = QtWidgets.QComboBox()
    self.comboBox_size.addItems([
      "Frigate (S)",
      "Cruiser (M)",
      "Battleship (L)",
      "Capital (XL)",
      "No Wormholes"
    ])

    self.checkBox_eol = QtWidgets.QCheckBox("Ignore EOL")
    self.checkBox_masscrit = QtWidgets.QCheckBox("Ignore critical mass")
    self.checkBox_ignore_old = QtWidgets.QCheckBox("Ignore wormholes >")
    self.spinBox_hours = QtWidgets.QSpinBox()
    self.spinBox_hours.setRange(0, 48)
    self.spinBox_hours.setValue(16)
    self.spinBox_hours.setSuffix(" h")

    # Avoidance
    self.lineEdit_system_avoid_name = QtWidgets.QLineEdit()
    self.lineEdit_system_avoid_name.setPlaceholderText("System name")
    self.pushButton_system_avoid_add = QtWidgets.QPushButton("Add")

    self.lineEdit_region_avoid_name = QtWidgets.QLineEdit()
    self.lineEdit_region_avoid_name.setPlaceholderText("Region name")
    self.pushButton_region_avoid_add = QtWidgets.QPushButton("Add")

    self.listWidget_avoid = QtWidgets.QListWidget()
    self.pushButton_avoid_delete = QtWidgets.QPushButton("Delete")
    self.pushButton_avoid_clear = QtWidgets.QPushButton("Clear")

    # Content
    self.label_status = QtWidgets.QLabel("")
    self.label_status.setAlignment(QtCore.Qt.AlignCenter)
    self.tableWidget_path = QtWidgets.QTableWidget()
    self.tableWidget_path.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    self.tableWidget_path.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    self.tableWidget_path.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    self.lineEdit_short_format = QtWidgets.QLineEdit()
    self.lineEdit_short_format.setReadOnly(True)
    self.lineEdit_short_format.setPlaceholderText("Short format route (click to copy)")

    self.pushButton_copy_clipboard = QtWidgets.QPushButton("Copy")
    self.pushButton_copy_clipboard.setToolTip("Copy route to clipboard")
    self.pushButton_copy_clipboard.setFixedWidth(60)

  def _setup_ui_layout(self):
    """
    Restructures the UI into a Sidebar + Main Content layout.
    """
    # Create new central widget
    new_central = QtWidgets.QWidget()
    main_layout = QtWidgets.QHBoxLayout(new_central)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # --- Left Sidebar ---
    sidebar = QtWidgets.QWidget()
    sidebar.setObjectName("sidebar")
    sidebar.setFixedWidth(320)
    sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(15, 15, 15, 15)
    sidebar_layout.setSpacing(15)

    # Header
    lbl_header = QtWidgets.QLabel("DAYTRIPPER")
    lbl_header.setObjectName("sidebar_header")
    sidebar_layout.addWidget(lbl_header)
    self.lbl_header = lbl_header

    # 1. Navigation Group
    sidebar_layout.addWidget(self._setup_navigation_group())

    # 2. Restrictions Group
    sidebar_layout.addWidget(self._setup_restrictions_group())

    # 3. Security & Avoidance
    sidebar_layout.addWidget(self._setup_security_group())
    sidebar_layout.addWidget(self._setup_avoidance_group())

    sidebar_layout.addStretch()

    self.pushButton_about = QtWidgets.QPushButton("About")
    self.pushButton_about.clicked.connect(self.open_about)
    sidebar_layout.addWidget(self.pushButton_about)

    # --- Right Main Area ---
    content = QtWidgets.QWidget()
    content.setObjectName("main_area")
    content_layout = QtWidgets.QVBoxLayout(content)
    content_layout.setContentsMargins(20, 20, 20, 20)
    content_layout.setSpacing(15)

    # Top Action Bar
    top_bar = QtWidgets.QHBoxLayout()
    top_bar.addStretch()
    top_bar.addWidget(self.pushButton_eve_login)
    top_bar.addWidget(self.pushButton_trip_config)
    top_bar.addWidget(self.pushButton_trip_get)
    content_layout.addLayout(top_bar)

    # Route Results Panel
    results_group = QtWidgets.QGroupBox("ROUTE RESULTS")
    results_layout = QtWidgets.QVBoxLayout(results_group)
    results_layout.setContentsMargins(10, 15, 10, 10)
    results_layout.setSpacing(10)
    
    results_layout.addWidget(self.label_status)
    results_layout.addWidget(self.tableWidget_path)

    # Floating action buttons below table
    row_table_actions = QtWidgets.QHBoxLayout()
    row_table_actions.addWidget(self.pushButton_set_dest)
    row_table_actions.addWidget(self.pushButton_player_location)
    row_table_actions.addStretch()
    
    # Copy Table Button (reusing existing logic)
    self.pushButton_copy_table = QtWidgets.QPushButton("Copy Table")
    self.pushButton_copy_table.clicked.connect(self.copy_table_to_clipboard)
    row_table_actions.addWidget(self.pushButton_copy_table)
    
    results_layout.addLayout(row_table_actions)
    content_layout.addWidget(results_group)

    # Copy-Paste Info Panel
    copy_panel = QtWidgets.QGroupBox("FC, please help! (Copy-paste info)")
    copy_layout = QtWidgets.QHBoxLayout(copy_panel)
    copy_layout.setContentsMargins(5, 15, 5, 5)
    copy_layout.setSpacing(0)
    
    copy_layout.addWidget(self.lineEdit_short_format)
    copy_layout.addWidget(self.pushButton_copy_clipboard)
    
    content_layout.addWidget(copy_panel)

    main_layout.addWidget(sidebar)
    main_layout.addWidget(content)
    self.setCentralWidget(new_central)

  def _apply_styles(self):
    style = """
    QMainWindow { background-color: #1b1e23; color: #dcdcdc; font-family: "Segoe UI", sans-serif; }
    
    /* Sidebar */
    QWidget#sidebar { background-color: #21252b; border-right: 1px solid #181a1f; }
    QLabel#sidebar_header { font-size: 14px; font-weight: bold; color: #abb2bf; padding: 5px; }
    
    /* GroupBoxes */
    QGroupBox { 
        border: 1px solid #3e4451; 
        border-radius: 4px; 
        margin-top: 10px; 
        font-weight: bold; 
        color: #abb2bf;
    }
    QGroupBox::title { 
        subcontrol-origin: margin; 
        subcontrol-position: top left; 
        padding: 0 5px; 
        left: 10px;
    }
    
    /* Inputs */
    QLineEdit { 
        background-color: #282c34; 
        border: 1px solid #3e4451; 
        border-radius: 3px; 
        padding: 6px; 
        color: #dcdcdc; 
    }
    QLineEdit:focus { border: 1px solid #00aaff; }
    
    /* Buttons */
    QPushButton { 
        background-color: #3e4451; 
        border: none; 
        border-radius: 3px; 
        padding: 8px 15px; 
        color: white; 
        font-weight: bold;
    }
    QPushButton:hover { background-color: #4b5263; }
    QPushButton:pressed { background-color: #2c313a; }
    QPushButton:disabled { background-color: #2c313a; color: #5c6370; }
    
    /* Specific Buttons */
    QPushButton#pushButton_find_path { 
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #007acc, stop:1 #005c99);
        border: 1px solid #005c99;
    }
    QPushButton#pushButton_find_path:hover { background-color: #008ae6; }
    
    QPushButton#pushButton_eve_login { background-color: #2c3e50; border: 1px solid #3e4451; }
    QPushButton#pushButton_trip_get { background-color: #b38600; color: #1b1e23; }
    QPushButton#pushButton_trip_get:hover { background-color: #e6ac00; }
    
    /* Table */
    QTableWidget { 
        background-color: #21252b; 
        border: 1px solid #3e4451; 
        gridline-color: #2c313a; 
        selection-background-color: #3e4451;
    }
    QHeaderView {
        background-color: #282c34;
    }
    QHeaderView::section:horizontal { 
        background-color: #282c34; 
        padding: 6px; 
        border: none; 
        border-bottom: 1px solid #3e4451;
        font-weight: bold;
        color: #abb2bf;
    }
    QHeaderView::section:vertical {
        padding: 0px;
        border: none;
        border-right: 1px solid #3e4451;
        color: #abb2bf;
    }
    QTableCornerButton::section {
        background-color: #282c34;
        border: 1px solid #3e4451;
    }
    
    /* Scrollbar */
    QScrollBar:vertical { background: #21252b; width: 12px; }
    QScrollBar::handle:vertical { background: #4b5263; border-radius: 6px; min-height: 20px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    
    /* Sliders */
    QSlider::groove:horizontal {
        border: 1px solid #3e4451;
        height: 6px;
        background: #282c34;
        margin: 2px 0;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #00aaff;
        border: 1px solid #00aaff;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
    """
    self.setStyleSheet(style)

  def _setup_security_group(self):
    group = QtWidgets.QGroupBox("Security Prioritization")
    group.setCheckable(True)
    layout = QtWidgets.QVBoxLayout(group)
    layout.setSpacing(5)

    def create_slider(label_text, attr_name, color):
      row = QtWidgets.QHBoxLayout()

      lbl = QtWidgets.QLabel(label_text)
      lbl.setFixedWidth(30)
      lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

      slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
      slider.setRange(1, 100)

      val_lbl = QtWidgets.QLabel("1")
      val_lbl.setFixedWidth(25)
      val_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

      # Update label when slider changes
      slider.valueChanged.connect(lambda v: val_lbl.setText(str(v)))

      row.addWidget(lbl)
      row.addWidget(slider)
      row.addWidget(val_lbl)

      layout.addLayout(row)

      setattr(self, attr_name, slider)
      setattr(self, attr_name + "_label", val_lbl)

    create_slider("HS", "slider_prio_hs", "#98c379")
    create_slider("LS", "slider_prio_ls", "#e5c07b")
    create_slider("NS", "slider_prio_ns", "#e06c75")
    create_slider("WH", "slider_prio_wh", "#61afef")

    # Replace the old groupbox reference so isChecked() works on the new one
    self.groupBox_security = group
    return group

  def _setup_avoidance_group(self):
    group = QtWidgets.QGroupBox("Avoidance List")
    group.setCheckable(True)
    # Preserve checked state if possible
    if hasattr(self, 'groupBox_avoidance'):
      group.setChecked(self.groupBox_avoidance.isChecked())

    layout = QtWidgets.QVBoxLayout(group)
    layout.setSpacing(5)

    # System Row
    row_sys = QtWidgets.QHBoxLayout()
    row_sys.addWidget(self.lineEdit_system_avoid_name)
    row_sys.addWidget(self.pushButton_system_avoid_add)
    layout.addLayout(row_sys)

    # Region Row
    row_reg = QtWidgets.QHBoxLayout()
    row_reg.addWidget(self.lineEdit_region_avoid_name)
    row_reg.addWidget(self.pushButton_region_avoid_add)
    layout.addLayout(row_reg)

    # List
    layout.addWidget(self.listWidget_avoid)

    # Actions
    row_act = QtWidgets.QHBoxLayout()
    row_act.addWidget(self.pushButton_avoid_delete)
    row_act.addWidget(self.pushButton_avoid_clear)
    layout.addLayout(row_act)

    # Replace the old groupbox reference so settings work on the new one
    self.groupBox_avoidance = group
    return group

  def _setup_navigation_group(self):
    group = QtWidgets.QGroupBox("Navigation")
    layout = QtWidgets.QVBoxLayout(group)
    layout.setSpacing(10)

    layout.addWidget(QtWidgets.QLabel("Source:"))
    layout.addWidget(self.lineEdit_source)
    layout.addWidget(QtWidgets.QLabel("Destination:"))
    layout.addWidget(self.lineEdit_destination)

    row_actions = QtWidgets.QHBoxLayout()
    row_actions.addWidget(self.pushButton_find_path)
    row_actions.addWidget(self.pushButton_reset)
    layout.addLayout(row_actions)

    self.progressBar_route = QtWidgets.QProgressBar()
    self.progressBar_route.setRange(0, 0)
    self.progressBar_route.setTextVisible(False)
    self.progressBar_route.setVisible(False)
    self.progressBar_route.setFixedHeight(5)
    layout.addWidget(self.progressBar_route)

    return group

  def _setup_restrictions_group(self):
    group = QtWidgets.QGroupBox("Wormhole Restrictions")
    layout = QtWidgets.QVBoxLayout(group)

    row_wh = QtWidgets.QHBoxLayout()
    row_wh.addWidget(QtWidgets.QLabel("Size:"))
    row_wh.addWidget(self.comboBox_size)
    layout.addLayout(row_wh)

    layout.addWidget(self.checkBox_eol)
    layout.addWidget(self.checkBox_masscrit)

    row_age = QtWidgets.QHBoxLayout()
    row_age.addWidget(self.checkBox_ignore_old)
    row_age.addWidget(self.spinBox_hours)
    layout.addLayout(row_age)

    return group

  # noinspection PyUnresolvedReferences
  def additional_gui_setup(self):
    # Additional GUI setup
    self.setWindowTitle(
      '{} v{} ({})'.format(
        __appname__,
        __version__,
        last_update,
      )
    )
    self._path_message("", MessageType.OK)
    self._avoid_message("", MessageType.OK)
    self.lineEdit_source.setFocus()
    self.lineEdit_short_format.mousePressEvent = partial(
      MainWindow.short_format_click, self
    )

    # Auto-completion
    system_list = self.nav.eve_db.system_name_list()
    system_list.sort(key=str.lower)
    for line_edit_field in [
        self.lineEdit_source,
        self.lineEdit_destination,
        self.lineEdit_system_avoid_name,
        self.lineEdit_set_dest,
    ]:
      completer = QtWidgets.QCompleter(system_list, self)
      completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
      completer.setModelSorting(
        QtWidgets.QCompleter.CaseInsensitivelySortedModel
      )
      line_edit_field.setCompleter(completer)

    region_list = self.nav.eve_db.region_name_list()
    region_list.sort(key=str.lower)
    completer = QtWidgets.QCompleter(region_list, self)
    completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
    completer.setModelSorting(QtWidgets.QCompleter.CaseInsensitivelySortedModel)
    completer.setFilterMode(QtCore.Qt.MatchContains)
    self.lineEdit_region_avoid_name.setCompleter(completer)

    # Signals
    self.pushButton_eve_login.clicked.connect(self.btn_eve_login_clicked)
    self.pushButton_player_location.clicked.connect(
      self.btn_player_location_clicked
    )
    self.pushButton_find_path.clicked.connect(self.btn_find_path_clicked)
    self.pushButton_trip_config.clicked.connect(self.btn_trip_config_clicked)
    self.pushButton_trip_get.clicked.connect(self.btn_trip_get_clicked)
    self.pushButton_system_avoid_add.clicked.connect(
      self.btn_system_avoid_add_clicked
    )
    self.pushButton_region_avoid_add.clicked.connect(
      self.btn_region_avoid_add_clicked
    )
    self.pushButton_avoid_delete.clicked.connect(self.btn_avoid_delete_clicked)
    self.pushButton_avoid_clear.clicked.connect(self.btn_avoid_clear_clicked)
    self.pushButton_set_dest.clicked.connect(self.btn_set_dest_clicked)
    self.pushButton_reset.clicked.connect(self.btn_reset_clicked)
    self.lineEdit_source.returnPressed.connect(self.line_edit_source_return)
    self.lineEdit_destination.returnPressed.connect(
      self.line_edit_destination_return
    )
    self.lineEdit_system_avoid_name.returnPressed.connect(
      self.line_edit_system_avoid_name_return
    )
    self.lineEdit_region_avoid_name.returnPressed.connect(
      self.line_edit_region_avoid_name_return
    )
    
    self.pushButton_copy_clipboard.clicked.connect(self.short_format_click_btn)
    self.lineEdit_set_dest.returnPressed.connect(self.btn_set_dest_clicked)
    self.tableWidget_path.itemSelectionChanged.connect(
      self.table_item_selection_changed
    )

    # Tab order
    self.setTabOrder(self.lineEdit_source, self.lineEdit_destination)
    self.setTabOrder(self.lineEdit_destination, self.pushButton_find_path)
    self.setTabOrder(self.pushButton_find_path, self.pushButton_reset)

    # Allow Enter key to trigger button when focused
    self.pushButton_find_path.setAutoDefault(True)

  def migrate_settings_tripwire(self):
    Logger.info('Mirgating Tripwire dialog settings to their own category')
    tripwire_url = self.settings.value('MainWindow/tripwire_url')
    tripwire_user = self.settings.value('MainWindow/tripwire_user')
    tripwire_pass = self.settings.value('MainWindow/tripwire_pass')
    evescout_enabled = self.settings.value(
      'MainWindow/evescout_enable', 'false'
    ) == 'true'
    self.settings.beginGroup('Tripwire')
    self.settings.setValue('url', tripwire_url)
    self.settings.setValue('user', tripwire_user)
    self.settings.setValue('pass', tripwire_pass)
    self.settings.setValue('evescout_enabled', evescout_enabled)
    self.settings.endGroup()
    self.settings.remove('MainWindow/tripwire_url')
    self.settings.remove('MainWindow/tripwire_user')
    self.settings.remove('MainWindow/tripwire_pass')
    self.settings.remove('MainWindow/evescout_enable')

  def read_settings_tripwire(self):
    self.global_proxy = self.settings.value('proxy')
    self.settings.beginGroup('Tripwire')
    self.tripwire_url = self.settings.value(
      'url', 'https://tripwire.eve-apps.com'
    )
    self.tripwire_user = self.settings.value('user')
    self.tripwire_pass = self.settings.value('pass')
    self.state_evescout["enabled"] = self.settings.value(
      'evescout_enabled', 'false'
    ) == 'true'
    self.auto_refresh_enabled = self.settings.value('auto_refresh_enabled', 'false') == 'true'
    self.auto_refresh_interval = int(self.settings.value('auto_refresh_interval', 30))
    self.settings.endGroup()

    self.settings.beginGroup('Pathfinder')
    self.pathfinder_url = self.settings.value('url', '')
    self.pathfinder_token = self.settings.value('token', '')
    self.pathfinder_enabled = self.settings.value('enabled', 'false') == 'true'
    self.settings.endGroup()

    self.settings.beginGroup('Wanderer')
    self.wanderer_url = self.settings.value('url', '')
    self.wanderer_map_id = self.settings.value('map_id', '')
    self.wanderer_token = self.settings.value('token', '')
    self.wanderer_enabled = self.settings.value('enabled', 'false') == 'true'
    self.settings.endGroup()

    self.update_auto_refresh_state()
    self.nav.setup_mappers()

    if self.tripwire_user and self.tripwire_pass:
      self.pushButton_trip_get.setEnabled(True)

  def read_settings(self):
    if self.settings.value('MainWindow/tripwire_url'):
      self.migrate_settings_tripwire()
    self.read_settings_tripwire()

    self.settings.beginGroup("MainWindow")

    # Window state
    win_geometry = self.settings.value("win_geometry")
    if win_geometry:
      self.restoreGeometry(win_geometry)
    win_state = self.settings.value("win_state")
    if win_state:
      self.restoreState(win_state)
    for col_idx, column_width in enumerate(
      self.settings.value("table_widths", "110,75,75,180").split(',')
    ):
      self.tableWidget_path.setColumnWidth(col_idx, int(column_width))

    # Avoidance list
    self.groupBox_avoidance.setChecked(
      self.settings.value("avoidance_enabled", "false") == "true"
    )
    for entity in self.settings.value("avoidance_list", "").split(','):
      if entity != "":
        self._avoid_entity_name(entity)

    # Restrictions
    self.comboBox_size.setCurrentIndex(
      int(self.settings.value("restrictions_whsize", "0"))
    )
    self.checkBox_eol.setChecked(
      self.settings.value("restriction_eol", "false") == "true"
    )
    self.checkBox_masscrit.setChecked(
      self.settings.value("restriction_masscrit", "false") == "true"
    )
    self.checkBox_ignore_old.setChecked(
      self.settings.value("restriction_ignore_old", "false") == "true"
    )
    self.spinBox_hours.setValue(
      int(float(self.settings.value("restriction_hours", "16.0")))
    )

    # Security prioritization
    self.groupBox_security.setChecked(
      self.settings.value("security_enabled", "false") == "true"
    )

    def set_slider(attr, val):
      slider = getattr(self, attr)
      slider.setValue(int(val))
      # Manually update label in case value didn't change from default
      getattr(self, attr + "_label").setText(str(slider.value()))

    set_slider("slider_prio_hs", self.settings.value("prio_hs", "1"))
    set_slider("slider_prio_ls", self.settings.value("prio_ls", "1"))
    set_slider("slider_prio_ns", self.settings.value("prio_ns", "1"))
    set_slider("slider_prio_wh", self.settings.value("prio_wh", "1"))

    self.settings.endGroup()

  def write_settings_tripwire(self):
    self.settings.setValue('proxy', self.global_proxy)
    self.settings.beginGroup('Tripwire')
    self.settings.setValue('url', self.tripwire_url)
    self.settings.setValue('user', self.tripwire_user)
    self.settings.setValue('pass', self.tripwire_pass)
    self.settings.setValue('evescout_enabled', self.state_evescout["enabled"])
    self.settings.setValue('auto_refresh_enabled', self.auto_refresh_enabled)
    self.settings.setValue('auto_refresh_interval', self.auto_refresh_interval)
    self.settings.endGroup()

    self.settings.beginGroup('Pathfinder')
    self.settings.setValue('url', self.pathfinder_url)
    self.settings.setValue('token', self.pathfinder_token)
    self.settings.setValue('enabled', self.pathfinder_enabled)
    self.settings.endGroup()

    self.settings.beginGroup('Wanderer')
    self.settings.setValue('url', self.wanderer_url)
    self.settings.setValue('map_id', self.wanderer_map_id)
    self.settings.setValue('token', self.wanderer_token)
    self.settings.setValue('enabled', self.wanderer_enabled)
    self.settings.endGroup()

  def write_settings(self):
    self.write_settings_tripwire()

    self.settings.beginGroup("MainWindow")

    # Window state
    self.settings.setValue("win_geometry", self.saveGeometry())
    self.settings.setValue("win_state", self.saveState())
    self.settings.setValue(
      "table_widths",
      ",".join([
        str(self.tableWidget_path.columnWidth(0)),
        str(self.tableWidget_path.columnWidth(1)),
        str(self.tableWidget_path.columnWidth(2)),
        str(self.tableWidget_path.columnWidth(3)),
      ]),
    )

    # Avoidance list
    self.settings.setValue(
      "avoidance_enabled", self.groupBox_avoidance.isChecked()
    )
    avoidance_list_string = ",".join(self.avoidance_list())
    self.settings.setValue("avoidance_list", avoidance_list_string)

    # Restrictions
    self.settings.setValue(
      "restrictions_whsize", self.comboBox_size.currentIndex()
    )
    self.settings.setValue("restriction_eol", self.checkBox_eol.isChecked())
    self.settings.setValue(
      "restriction_masscrit", self.checkBox_masscrit.isChecked()
    )
    self.settings.setValue(
      "restriction_ignore_old", self.checkBox_ignore_old.isChecked()
    )
    self.settings.setValue(
      "restriction_hours", self.spinBox_hours.value()
    )

    # Security prioritization
    self.settings.setValue(
      "security_enabled", self.groupBox_security.isChecked()
    )
    self.settings.setValue("prio_hs", self.slider_prio_hs.value())
    self.settings.setValue("prio_ls", self.slider_prio_ls.value())
    self.settings.setValue("prio_ns", self.slider_prio_ns.value())
    self.settings.setValue("prio_wh", self.slider_prio_wh.value())

    self.settings.endGroup()

  def _message_box(self, title, text):
    msg_box = QtWidgets.QMessageBox(self)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    return msg_box.exec()

  @staticmethod
  def _label_message(label, message, message_type):
    # FIXME(secondfry): set only color, not entire stylesheet.
    if message_type == MessageType.OK:
      label.setStyleSheet("QLabel {color: #98c379;}")
    elif message_type == MessageType.ERROR:
      label.setStyleSheet("QLabel {color: #e06c75;}")
    else:
      label.setStyleSheet("QLabel {color: #abb2bf;}")
    label.setText(message)

  def _avoid_message(self, message, message_type):
    self.statusBar().showMessage(message, 5000)

  def _path_message(self, message, message_type):
    MainWindow._label_message(self.label_status, message, message_type)

  def _status_eve_connection(self, message, message_type=MessageType.INFO):
    MainWindow._label_message(self.status_eve_connection, message, message_type)

  def _status_evescout(self, message, message_type=MessageType.INFO):
    MainWindow._label_message(self.status_evescout, message, message_type)

  def _status_tripwire(self, message, message_type=MessageType.INFO):
    MainWindow._label_message(self.status_tripwire, message, message_type)

  def avoidance_enabled(self) -> bool:
    return self.groupBox_avoidance.isChecked()

  def avoidance_list(self) -> List[str]:
    items: List[str] = []
    for idx in range(self.listWidget_avoid.count()):
      item: QtWidgets.QListWidgetItem = self.listWidget_avoid.item(idx)
      items.append(item.text())
    return items

  def _avoid_entity_name(self, name):
    if not name:
      self._avoid_message("Avoidance list: invalid name :(", MessageType.ERROR)
      return

    if name in self.avoidance_list():
      self._avoid_message(
        "Avoidance list: {} is already in the list!".format(name),
        MessageType.ERROR
      )
      return

    QtWidgets.QListWidgetItem(name, self.listWidget_avoid)
    self._avoid_message("Avoidance list: {} added".format(name), MessageType.OK)

  def avoid_system(self):
    sys_name = self.nav.eve_db.normalize_name(
      self.lineEdit_system_avoid_name.text()
    )
    self._avoid_entity_name(sys_name)

  def avoid_region(self):
    region_name = self.nav.eve_db.normalize_region_name(
      self.lineEdit_region_avoid_name.text()
    )
    self._avoid_entity_name(region_name)

  @staticmethod
  def get_system_class_color(sclass):
    if sclass.startswith('C') or sclass == 'WH':
      return QtGui.QColor("#4fc3f7")  # Bright Blue

    return {
      'HS': QtGui.QColor("#81c784"),  # Bright Green
      'LS': QtGui.QColor("#fff176"),  # Bright Yellow
      'NS': QtGui.QColor("#e57373"),  # Bright Red
      '▲': QtGui.QColor("#e57373"),   # Bright Red
      'Z': QtGui.QColor("#e57373"),   # Bright Red
    }.get(sclass, QtGui.QColor("#e0e0e0"))

  def add_data_to_table(self, route):
    self.tableWidget_path.setRowCount(len(route))

    for route_step_id, route_step in enumerate(route):
      color = self.get_system_class_color(route_step['class'])

      route_step['security'] = round(route_step['security'], 1)
      ui_col_id = 0
      for col_id in [
          'name',
          'class',
          'security',
          'path_action',
          'path_info',
      ]:
        text = str(route_step[col_id])
        item = QtWidgets.QTableWidgetItem(text)

        if col_id in ['class', 'security']:
          item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
          item.setForeground(color)
          font = item.font()
          font.setBold(True)
          item.setFont(font)

        if col_id == 'path_action' and 'wormhole' in text:
          item.setIcon(self.icon_wormhole)

        self.tableWidget_path.setItem(route_step_id, ui_col_id, item)
        ui_col_id += 1

    self.tableWidget_path.resizeRowsToContents()

  def get_restrictions_size(self) -> Dict[WormholeSize, bool]:
    size_restriction = {
      WormholeSize.SMALL: True,
      WormholeSize.MEDIUM: True,
      WormholeSize.LARGE: True,
      WormholeSize.XLARGE: True,
    }

    combo_index = self.comboBox_size.currentIndex()
    if combo_index < 1:
      size_restriction[WormholeSize.SMALL] = False
    if combo_index < 2:
      size_restriction[WormholeSize.MEDIUM] = False
    if combo_index < 3:
      size_restriction[WormholeSize.LARGE] = False
    if combo_index < 4:
      size_restriction[WormholeSize.XLARGE] = False

    return size_restriction

  def get_restrictions_age(self) -> float:
    age_threshold = float('inf')

    if self.checkBox_ignore_old.isChecked():
      age_threshold = float(self.spinBox_hours.value())

    return age_threshold

  def get_restrictions_security(self) -> Dict[SpaceType, int]:
    security_prio = {
      SpaceType.HS: 1,
      SpaceType.LS: 1,
      SpaceType.NS: 1,
      SpaceType.WH: 1,
    }

    if self.groupBox_security.isChecked():
      security_prio[SpaceType.HS] = self.slider_prio_hs.value()
      security_prio[SpaceType.LS] = self.slider_prio_ls.value()
      security_prio[SpaceType.NS] = self.slider_prio_ns.value()
      security_prio[SpaceType.WH] = self.slider_prio_wh.value()

    return security_prio

  def get_restrictions_avoidance(self) -> List[int]:
    if not self.avoidance_enabled():
      return []

    res = []
    for entity in self.avoidance_list():
      idx = self.eve_db.name2id(entity)

      if idx:
        res.append(idx)
        continue

      idx = self.eve_db.region_name_to_id(entity)

      if not idx:
        continue

      res.extend(self.eve_db.get_region_system_ids(idx))

    return res

  def get_restrictions(self) -> Restrictions:
    size_restriction = self.get_restrictions_size()
    ignore_eol = self.checkBox_eol.isChecked()
    ignore_masscrit = self.checkBox_masscrit.isChecked()
    age_threshold = self.get_restrictions_age()
    security_prio = self.get_restrictions_security()
    avoidance_list = self.get_restrictions_avoidance()

    return {
      "size_restriction": size_restriction,
      "ignore_eol": ignore_eol,
      "ignore_masscrit": ignore_masscrit,
      "age_threshold": age_threshold,
      "security_prio": security_prio,
      "avoidance_list": avoidance_list,
    }

  def _clear_results(self):
    self.tableWidget_path.setRowCount(0)
    self.lineEdit_short_format.setText("")

  def find_path(self):
    source_sys_name = self.nav.eve_db.normalize_name(
      self.lineEdit_source.text().strip()
    )
    dest_sys_name = self.nav.eve_db.normalize_name(
      self.lineEdit_destination.text().strip()
    )

    if not source_sys_name or not dest_sys_name:
      self._clear_results()
      error_msg = []
      if not source_sys_name:
        error_msg.append("source")
      if not dest_sys_name:
        error_msg.append("destination")
      error_msg = "Invalid system name in {}.".format(" and ".join(error_msg))
      self._path_message(error_msg, MessageType.ERROR)
      return

    self.pushButton_find_path.setEnabled(False)
    self._path_message("Calculating route...", MessageType.INFO)
    self.progressBar_route.setVisible(True)
    self.start_route_calculation.emit(
      self.eve_db.name2id(source_sys_name),
      self.eve_db.name2id(dest_sys_name),
    )

  @QtCore.Slot(list, str)
  def route_result_handler(self, route, short_format):
    self.pushButton_find_path.setEnabled(True)
    self.progressBar_route.setVisible(False)

    if not route:
      self._clear_results()
      self._path_message(
        "No path found between the solar systems.", MessageType.ERROR
      )
      return

    route_length = len(route)
    if route_length == 1:
      self._path_message(
        "Set the same source and destination :P", MessageType.OK
      )
    else:
      self.label_status.setText("{} JUMPS".format(route_length - 1))
      self.label_status.setStyleSheet("QLabel {color: white; font-weight: bold;}")

    self.add_data_to_table(route)
    self.lineEdit_short_format.setText(short_format)

  def short_format_click(self, event):
    event.accept()
    if not self.lineEdit_short_format.text():
      return
    self.lineEdit_short_format.selectAll()
    self.lineEdit_short_format.copy()
    self.statusBar().showMessage("Copied travel info to clipboard!", 5000)

  def short_format_click_btn(self):
    if not self.lineEdit_short_format.text():
      return
    self.lineEdit_short_format.selectAll()
    self.lineEdit_short_format.copy()
    self.statusBar().showMessage("Copied travel info to clipboard!", 5000)

  @QtCore.Slot()
  def copy_table_to_clipboard(self):
    if self.tableWidget_path.rowCount() == 0:
      self.statusBar().showMessage("No route to copy!", 3000)
      return

    text_data = []
    headers = []
    for col in range(self.tableWidget_path.columnCount()):
      item = self.tableWidget_path.horizontalHeaderItem(col)
      headers.append(item.text() if item else "")
    text_data.append("\t".join(headers))

    for row in range(self.tableWidget_path.rowCount()):
      row_data = []
      for col in range(self.tableWidget_path.columnCount()):
        item = self.tableWidget_path.item(row, col)
        row_data.append(item.text() if item else "")
      text_data.append("\t".join(row_data))

    clipboard = QtGui.QGuiApplication.clipboard()
    clipboard.setText("\n".join(text_data))
    self.statusBar().showMessage("Route table copied to clipboard!", 5000)

  def _status_eve_connection_update(self):
    if self.state_eve_connection["connected"]:
      self._status_eve_connection(
        "EVE connection: {}".format(self.state_eve_connection["char_name"]),
        MessageType.OK
      )
      self.pushButton_eve_login.setText("Logout")
      self.pushButton_player_location.setEnabled(True)
      self.pushButton_set_dest.setEnabled(True)
      
      # Update Header with Character Name
      if hasattr(self, 'lbl_header'):
        self.lbl_header.setText(f"DAYTRIPPER <span style='color: #61afef'>{self.state_eve_connection['char_name'].upper()}</span>")
      return

    if self.state_eve_connection["error"]:
      self._status_eve_connection(
        "EVE connection: {}".format(self.state_eve_connection["error"]),
        MessageType.ERROR
      )
      return

    self._status_eve_connection("EVE connection: absent")
    self.pushButton_eve_login.setText("Log in with EvE")
    self.pushButton_player_location.setEnabled(False)
    self.pushButton_set_dest.setEnabled(False)
    
    # Reset Header
    if hasattr(self, 'lbl_header'):
      self.lbl_header.setText("DAYTRIPPER")

  def _status_evescout_update(self):
    if not self.state_evescout["enabled"]:
      self._status_evescout("Eve-Scout: disabled")
      return

    if self.state_evescout["error"]:
      self._status_evescout("Eve-Scout: disabled", MessageType.ERROR)
      return

    if not self.state_evescout["connections"]:
      self._status_evescout("Eve-Scout: enabled")
      return

    self._status_evescout(
      "Eve-Scout: {} connections".format(self.state_evescout["connections"]),
      MessageType.OK
    )

  def _status_tripwire_update(self):
    if self.state_tripwire["error"]:
      self._status_tripwire("Tripwire: error", MessageType.ERROR)
      return

    if not self.state_tripwire["connections"]:
      self._status_tripwire("Tripwire: enabled")
      return

    self._status_tripwire(
      "Tripwire: {} connections".format(self.state_tripwire["connections"]),
      MessageType.OK
    )

  def _status_pathfinder_update(self):
    if not self.pathfinder_enabled:
      self._label_message(self.status_pathfinder, "Pathfinder: disabled", MessageType.INFO)
      return

    if self.state_pathfinder["error"]:
      self._label_message(self.status_pathfinder, "Pathfinder: error", MessageType.ERROR)
      return

    if not self.state_pathfinder["connections"]:
      self._label_message(self.status_pathfinder, "Pathfinder: enabled", MessageType.INFO)
      return

    self._label_message(
      self.status_pathfinder,
      "Pathfinder: {} connections".format(self.state_pathfinder["connections"]),
      MessageType.OK
    )

  def _status_wanderer_update(self):
    if not self.wanderer_enabled:
      self._label_message(self.status_wanderer, "Wanderer: disabled", MessageType.INFO)
      return

    if self.state_wanderer["error"]:
      self._label_message(self.status_wanderer, "Wanderer: error", MessageType.ERROR)
      return

    if not self.state_wanderer["connections"]:
      self._label_message(self.status_wanderer, "Wanderer: enabled", MessageType.INFO)
      return

    self._label_message(
      self.status_wanderer,
      "Wanderer: {} connections".format(self.state_wanderer["connections"]),
      MessageType.OK
    )

  @QtCore.Slot(str)
  def login_handler(self, is_ok, char_name):
    self.state_eve_connection["connected"] = is_ok
    self.state_eve_connection["char_name"] = char_name
    self.state_eve_connection["error"] = "ESI error" if not is_ok else None
    self._status_eve_connection_update()

  @QtCore.Slot()
  def logout_handler(self):
    self.state_eve_connection["connected"] = False
    self.state_eve_connection["char_name"] = None
    self.state_eve_connection["error"] = None
    self._status_eve_connection_update()

  @QtCore.Slot(str)
  def location_handler(self, location):
    if location:
      self.lineEdit_source.setText(location)
    else:
      self._message_box(
        "Player destination",
        "Unable to get location (character not online or ESI error)"
      )
    self.pushButton_player_location.setEnabled(True)

  @QtCore.Slot(bool)
  def destination_handler(self, response):
    if not response:
      self._message_box(
        "Player destination", "ESI error when trying to set destination"
      )
    self.pushButton_set_dest.setEnabled(True)

  @QtCore.Slot(dict)
  def worker_thread_done(self, results):
    self.worker_thread.quit()

    # wait for thread to finish
    while self.worker_thread.isRunning():
      time.sleep(0.01)

    # Eve Scout
    evescout_connections = results.get("Eve Scout", 0)
    self.state_evescout["connections"] = evescout_connections
    if evescout_connections < 0:
      self.state_evescout["error"] = "error"
    self._status_evescout_update()

    # Tripwire
    connections = results.get("Tripwire", 0)
    self.state_tripwire["connections"] = connections
    if connections < 0:
      self.state_tripwire["error"] = "error. Check url/user/pass."
    self._status_tripwire_update()

    # Pathfinder
    pf_connections = results.get("Pathfinder", 0)
    self.state_pathfinder["connections"] = pf_connections
    self.state_pathfinder["error"] = "error" if pf_connections < 0 else None
    self._status_pathfinder_update()

    # Wanderer
    wanderer_connections = results.get("Wanderer", 0)
    self.state_wanderer["connections"] = wanderer_connections
    self.state_wanderer["error"] = "error" if wanderer_connections < 0 else None
    self._status_wanderer_update()

    if self.tripwire_user and self.tripwire_pass:
      self.pushButton_trip_get.setEnabled(True)
    self.pushButton_find_path.setEnabled(True)

  @QtCore.Slot()
  def btn_eve_login_clicked(self):
    if not self.state_eve_connection["connected"]:
      self.esip.login()
    else:
      self.esip.logout()

  @QtCore.Slot()
  def btn_player_location_clicked(self):
    self.pushButton_player_location.setEnabled(False)
    self.esip.get_location()

  @QtCore.Slot()
  def btn_set_dest_clicked(self):
    if self.pushButton_set_dest.isEnabled():
      dest_sys_name = self.nav.eve_db.normalize_name(
        self.lineEdit_set_dest.text().strip()
      )
      sys_id = self.nav.eve_db.name2id(dest_sys_name)
      if sys_id:
        self.pushButton_set_dest.setEnabled(False)
        self.esip.set_destination(sys_id)
      else:
        if self.lineEdit_set_dest.text().strip() == "":
          msg_txt = "No system name give as input"
        else:
          msg_txt = "Invalid system name: '{}'".format(
            self.lineEdit_set_dest.text()
          )
        self._message_box("Player destination", msg_txt)

  @QtCore.Slot()
  def btn_find_path_clicked(self):
    self.find_path()

  @QtCore.Slot()
  def btn_trip_config_clicked(self):
    tripwire_dialog = TripwireDialog(
      self.tripwire_url,
      self.tripwire_user,
      self.tripwire_pass,
      self.global_proxy,
      self.state_evescout["enabled"],
      self.auto_refresh_enabled,
      self.auto_refresh_interval,
      self.clear_tripwire_cookies,
      self.test_tripwire_connection,
      self.test_pathfinder_connection,
      self.pathfinder_url,
      self.pathfinder_token,
      self.pathfinder_enabled,
      self.test_wanderer_connection,
      self.wanderer_url,
      self.wanderer_map_id,
      self.wanderer_token,
      self.wanderer_enabled,
    )

    if not tripwire_dialog.exec():
      return

    self.tripwire_url = tripwire_dialog.lineEdit_url.text()
    self.tripwire_user = tripwire_dialog.lineEdit_user.text()
    self.tripwire_pass = tripwire_dialog.lineEdit_pass.text()
    self.global_proxy = tripwire_dialog.lineEdit_proxy.text()

    self.pathfinder_url = tripwire_dialog.lineEdit_pf_url.text()
    self.pathfinder_token = tripwire_dialog.lineEdit_pf_token.text()
    self.pathfinder_enabled = tripwire_dialog.checkBox_pf_enabled.isChecked()

    self.wanderer_url = tripwire_dialog.lineEdit_wanderer_url.text()
    self.wanderer_map_id = tripwire_dialog.lineEdit_wanderer_map_id.text()
    self.wanderer_token = tripwire_dialog.lineEdit_wanderer_token.text()
    self.wanderer_enabled = tripwire_dialog.checkBox_wanderer_enabled.isChecked()

    self.nav.setup_mappers()
    self.state_evescout["enabled"
                        ] = tripwire_dialog.checkBox_evescout.isChecked()
    
    self.auto_refresh_enabled = tripwire_dialog.checkBox_auto_refresh.isChecked()
    self.auto_refresh_interval = tripwire_dialog.spinBox_interval.value()
    self.update_auto_refresh_state()

    self._status_evescout_update()
    self._status_pathfinder_update()
    self._status_wanderer_update()
    self.write_settings_tripwire()

    if self.tripwire_user and self.tripwire_pass:
      if not self.worker_thread.isRunning():
        self.pushButton_trip_get.setEnabled(True)
    else:
      self.pushButton_trip_get.setEnabled(False)

  def update_auto_refresh_state(self):
    self.auto_refresh_timer.setInterval(self.auto_refresh_interval * 1000)
    if self.auto_refresh_enabled and self.tripwire_user and self.tripwire_pass:
      if not self.auto_refresh_timer.isActive():
        self.auto_refresh_timer.start()
    else:
      self.auto_refresh_timer.stop()

  @QtCore.Slot()
  def btn_trip_get_clicked(self):
    if not self.worker_thread.isRunning():
      self.pushButton_trip_get.setEnabled(False)
      self.pushButton_find_path.setEnabled(False)
      self.nav_processor.evescout_enable = self.state_evescout["enabled"]
      self.worker_thread.start()
    else:
      self.state_tripwire['error'] = "error. Process is already running."
      self._status_tripwire_update()

  def clear_tripwire_cookies(self):
    if self.nav.tripwire_instance:
      self.nav.tripwire_instance.clear_cookies()
    self._message_box("Tripwire", "Cookies cleared!")

  def test_tripwire_connection(self, url, user, password, proxy):
    from shortcircuit.model.tripwire import Tripwire

    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
      tw = Tripwire(user, password, url)
      success, message = tw.test_credentials(proxy)
    except Exception as e:
      success = False
      message = str(e)
    finally:
      QtWidgets.QApplication.restoreOverrideCursor()

    self._message_box("Tripwire Connection", f"{'Success' if success else 'Failed'}: {message}")

  def test_pathfinder_connection(self, url, token):
    from shortcircuit.model.pathfinder import Pathfinder

    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
      pf = Pathfinder(url, token)
      success, message = pf.test_credentials()
    except Exception as e:
      success = False
      message = str(e)
    finally:
      QtWidgets.QApplication.restoreOverrideCursor()

    self._message_box("Pathfinder Connection", f"{'Success' if success else 'Failed'}: {message}")

  def test_wanderer_connection(self, url, map_id, token):
    from shortcircuit.model.wanderer import Wanderer

    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
      wd = Wanderer(url, map_id, token)
      success, message = wd.test_credentials()
    except Exception as e:
      success = False
      message = str(e)
    finally:
      QtWidgets.QApplication.restoreOverrideCursor()

    self._message_box("Wanderer Connection", f"{'Success' if success else 'Failed'}: {message}")

  @QtCore.Slot()
  def auto_refresh_triggered(self):
    if not self.worker_thread.isRunning() and self.tripwire_user and self.tripwire_pass:
      self.btn_trip_get_clicked()
    elif self.worker_thread.isRunning():
      # Silently skip if already running to avoid spamming status bar
      pass
    else:
      # Credentials missing or other issue
      self.state_tripwire['error'] = "Auto-refresh failed: check credentials"
      self._status_tripwire_update()

  @QtCore.Slot()
  def btn_system_avoid_add_clicked(self):
    self.avoid_system()

  @QtCore.Slot()
  def btn_region_avoid_add_clicked(self):
    self.avoid_region()

  @QtCore.Slot()
  def btn_avoid_delete_clicked(self):
    for item in self.listWidget_avoid.selectedItems():
      self.listWidget_avoid.takeItem(self.listWidget_avoid.row(item))

  @QtCore.Slot()
  def btn_avoid_clear_clicked(self):
    self.listWidget_avoid.clear()

  @QtCore.Slot()
  def btn_reset_clicked(self):
    msg_box = QtWidgets.QMessageBox(self)
    msg_box.setWindowTitle("Reset chain")
    msg_box.setText("Are you sure you want to clear all Tripwire data?")
    msg_box.setStandardButtons(
      QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
    )
    msg_box.setDefaultButton(QtWidgets.QMessageBox.No)
    ret = msg_box.exec()

    if ret == QtWidgets.QMessageBox.Yes:
      self.nav.reset_chain()
      self.state_evescout["connections"] = 0
      self.state_tripwire["connections"] = 0
      self.state_pathfinder["connections"] = 0
      self.state_wanderer["connections"] = 0
      self._status_pathfinder_update()
      self._status_wanderer_update()
      self._status_evescout_update()
      self._status_tripwire_update()

  @QtCore.Slot()
  def line_edit_system_avoid_name_return(self):
    self.avoid_system()

  @QtCore.Slot()
  def line_edit_region_avoid_name_return(self):
    self.avoid_region()

  @QtCore.Slot()
  def line_edit_source_return(self):
    self.lineEdit_destination.setFocus()

  @QtCore.Slot()
  def line_edit_destination_return(self):
    self.find_path()

  def _table_style(self, red_value, green_value, blue_value):
    self.tableWidget_path.setStyleSheet(
      "selection-color: white; selection-background-color: rgb({}, {}, {});".
      format(
        red_value,
        green_value,
        blue_value,
      )
    )

  @QtCore.Slot()
  def table_item_selection_changed(self):
    selection = self.tableWidget_path.selectedItems()
    if selection:
      sys_class = selection[1].text()
      if sys_class == "HS":
        self._table_style(60, 90, 60)
      elif sys_class == "LS":
        self._table_style(90, 80, 40)
      elif sys_class == "NS":
        self._table_style(90, 50, 50)
      else:
        self._table_style(50, 70, 90)

      self.lineEdit_set_dest.setText(selection[0].text())

  def open_about(self):
    AboutDialog(self.trigger_version_check, self).exec()

  def trigger_version_check(self):
    self._path_message("Checking for updates...", MessageType.INFO)
    self.start_version_check.emit()

  @QtCore.Slot(str)
  def version_check_done(self, latest):
    if not latest:
      return

    latest = json.loads(latest)
    version = latest['tag_name'].split('v')[-1]
    changelog = latest['body']
    if len(latest['body']) > 1200:
      changelog = latest['body'][0:1200].split(' ')
      del changelog[-1]
      changelog = ' '.join(changelog)

    version_box = QtWidgets.QMessageBox(self)
    version_box.setWindowTitle('New version available!')
    version_box.setText(
      'Your version: v{} ({}).\nGitHub latest release: v{} ({}).\n\n{}'.format(
        __version__,
        last_update,
        version,
        latest['published_at'],
        changelog,
      )
    )
    version_box.addButton('Download now', QtWidgets.QMessageBox.AcceptRole)
    version_box.addButton('Remind me later', QtWidgets.QMessageBox.RejectRole)
    ret = version_box.exec()

    if ret != QtWidgets.QMessageBox.AcceptRole:
      return

    QtGui.QDesktopServices.openUrl(
      QtCore.QUrl(
        'https://github.com/secondfry/shortcircuit/releases/tag/{}'.format(
          latest['tag_name']
        )
      )
    )

  # event: QCloseEvent
  def closeEvent(self, event):
    self.write_settings()
    
    # Clean up completers to prevent crash on exit
    for line_edit in [
        self.lineEdit_source,
        self.lineEdit_destination,
        self.lineEdit_system_avoid_name,
        self.lineEdit_set_dest,
        self.lineEdit_region_avoid_name,
    ]:
      line_edit.setCompleter(None)

    self.route_thread.quit()
    self.route_thread.wait()
    
    self.worker_thread.quit()
    self.worker_thread.wait()
    
    self.version_thread.quit()
    self.version_thread.wait()
    
    event.accept()


def run():
  appl = QtWidgets.QApplication(sys.argv)
  if hasattr(qdarktheme, 'setup_theme'):
    qdarktheme.setup_theme()
  elif hasattr(qdarktheme, 'load_stylesheet'):
    appl.setStyleSheet(qdarktheme.load_stylesheet())
  form = MainWindow()
  form.show()
  appl.exec()


if __name__ == "__main__":
  run()
