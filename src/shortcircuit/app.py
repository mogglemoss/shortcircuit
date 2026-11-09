# app.py

from enum import Enum
import json
import os
import sys
import time
from functools import partial
from typing import Dict, List, TypedDict, Union
import webbrowser

from appdirs import AppDirs
from PySide6 import QtCore, QtGui, QtWidgets, QtNetwork

from . import __appname__, __appslug__, __date__ as last_update, __version__
from .mapper_dialogs import MappersDialog
from .model.esi_processor import ESIProcessor
from .model.evedb import EveDb, Restrictions, SpaceType, WormholeSize
from .model.logger import Logger
from .model.mapper_config import (
    MapperConfig,
    default_configs,
    load_configs,
    migrate_legacy,
    save_configs,
)
from .model.navigation import Navigation
from .model.navprocessor import NavProcessor
from .model.versioncheck import VersionCheck
from . import brands
from .theme import theme
from .view import resources_rc  # noqa: F401 — registers Qt resources (:/images/...)


class StateEVEConnection(TypedDict):
    connected: bool
    char_name: Union[str, None]
    char_id: int
    error: Union[str, None]


class StateMapper(TypedDict):
    connections: int
    error: Union[str, None]


class MessageType(Enum):
    INFO = 0
    ERROR = 1
    OK = 2


# Main window stylesheet. Colors are theme tokens (@name), resolved by
# theme.qss() for the active mode; see theme.py.
MAIN_QSS = """
    /* No font-family override: "Segoe UI" is a Windows font, and forcing
       it makes macOS/Linux substitute something ugly. Each platform's
       native UI font is the right answer. */
    QMainWindow { background-color: @window; color: @text; }

    /* Sidebar */
    QWidget#sidebar { background-color: @panel; border-right: 1px solid @sidebar_edge; }
    /* No padding: the name must sit flush-left with the status line below it. */
    QLabel#sidebar_header { font-size: 14px; font-weight: bold; color: @text_secondary; padding: 0; }

    /* GroupBoxes */
    QGroupBox {
        border: 1px solid @border;
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 10px;
        font-weight: bold;
        color: @text_secondary;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
    }

    /* Inputs */
    QLineEdit {
        background-color: @field;
        border: 1px solid @border;
        border-radius: 3px;
        padding: 6px;
        color: @text;
    }
    QLineEdit:focus { border: 1px solid @focus; }

    /* Buttons */
    QPushButton {
        background-color: @button;
        border: none;
        border-radius: 3px;
        padding: 8px 15px;
        color: @on_button;
        font-weight: bold;
    }
    QPushButton:hover { background-color: @button_hover; }
    QPushButton:pressed { background-color: @button_pressed; }
    QPushButton:disabled { background-color: @button_disabled; color: @text_faint; }

    /* Specific Buttons */
    QPushButton#pushButton_find_path {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 @primary_top, stop:1 @primary_bottom);
        border: 1px solid @primary_bottom;
        color: @on_primary;
    }
    QPushButton#pushButton_find_path:hover { background-color: @primary_hover; }

    QPushButton#pushButton_trip_get { background-color: @action; color: @on_action; }
    QPushButton#pushButton_trip_get:hover { background-color: @action_hover; }

    /* Table: no vertical gridlines (cells breathe instead of touching
       rules), zebra rows, generous cell padding, padded headers. */
    QTableWidget {
        background-color: @panel;
        alternate-background-color: @row_alt;
        border: 1px solid @border;
        selection-background-color: @selection;
        font-size: 13px;
    }
    QTableWidget::item {
        padding: 6px 12px;
        border: none;
        border-bottom: 1px solid @divider;
    }
    QHeaderView {
        background-color: @field;
    }
    QHeaderView::section:horizontal {
        background-color: @field;
        padding: 8px 12px;
        border: none;
        border-bottom: 1px solid @border;
        font-weight: bold;
        color: @text_secondary;
    }
    QHeaderView::section:vertical {
        background-color: @panel;
        padding: 0 10px;
        border: none;
        border-bottom: 1px solid @divider;
        color: @text_faint;
        font-size: 11px;
    }
    QTableCornerButton::section {
        background-color: @field;
        border: none;
        border-bottom: 1px solid @border;
    }

    /* Scrollbar */
    QScrollBar:vertical { background: @panel; width: 12px; }
    QScrollBar::handle:vertical { background: @scroll_handle; border-radius: 6px; min-height: 20px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

    /* Sliders */
    QSlider::groove:horizontal {
        border: 1px solid @border;
        height: 6px;
        background: @field;
        margin: 2px 0;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: @focus;
        border: 1px solid @focus;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }

    /* Compact buttons sit beside line edits and must match their height */
    QPushButton[compact="true"] {
        padding: 6px 12px;
    }

    /* Route bar glyph buttons (locate / swap) */
    QPushButton#btn_glyph_locate, QPushButton#btn_glyph_swap {
        font-size: 17px;
        padding: 0;
    }

    /* Appearance menu button: the drop-down arrow sits beside the label */
    QPushButton#pushButton_theme {
        padding-right: 26px;
    }
    QPushButton#pushButton_theme::menu-indicator {
        subcontrol-origin: padding;
        subcontrol-position: right center;
        right: 10px;
    }

    /* Mapper status pill (clickable; hover confirms it) */
    QLabel#status_pill {
        border: 1px solid @border;
        border-radius: 14px;
        padding: 6px 14px;
    }
    QLabel#status_pill:hover {
        border-color: @link;
        background-color: @hover_surface;
    }

    /* Hero route bar */
    QWidget#route_bar {
        background-color: @panel;
        border: 1px solid @border;
        border-radius: 6px;
    }
    QWidget#route_bar QLineEdit {
        font-size: 15px;
        padding: 9px 12px;
    }
    QWidget#route_bar QPushButton {
        font-size: 15px;
    }

    /* Transient toast */
    QLabel#toast {
        background-color: @field;
        border: 1px solid @border;
        border-radius: 4px;
        padding: 8px 14px;
        color: @text;
    }

    /* Popup Menus */
    QMenu {
        background-color: @panel;
        border: 1px solid @border;
        color: @text;
    }
    QMenu::item {
        padding: 5px 25px 5px 20px;
        border: 1px solid transparent;
    }
    QMenu::item:selected {
        background-color: @selection;
        border-color: @focus;
    }
    QMenu::separator {
        height: 1px;
        background: @border;
        margin: 5px 10px;
    }
"""


class ClickableLabel(QtWidgets.QLabel):
    """Status-bar label that acts as a link: click emits `clicked`."""

    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        event.accept()


class NameLabel(QtWidgets.QLabel):
    """
    Character-name label that fits whatever width the layout gives it.

    EVE names run up to 37 characters, far wider than the space beside the
    portrait. The name wraps at spaces onto at most `max_lines` lines; text
    that still doesn't fit (a single very long word, or more words than
    lines) ends in an ellipsis and the full name moves to the tooltip.
    QLabel's own word wrap can't do this: it never breaks or elides a word
    longer than the line, it just clips it.
    """

    def __init__(self, text="", max_lines=2, parent=None):
        super().__init__(parent)
        self._full_text = text
        self._max_lines = max_lines
        # Character and corp names are data, never markup.
        self.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        # Take the width the row offers instead of demanding the full
        # single-line width of the name.
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        super().setText(text)

    def full_text(self):
        return self._full_text

    def setText(self, text):
        self._full_text = text
        self._refit()

    def minimumSizeHint(self):
        return QtCore.QSize(0, super().minimumSizeHint().height())

    def sizeHint(self):
        return QtCore.QSize(0, super().sizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refit()

    def changeEvent(self, event):
        # Stylesheet changes (the name turns bold blue on login) change the
        # font metrics, so the fit has to be recomputed.
        super().changeEvent(event)
        if event.type() in (QtCore.QEvent.Type.FontChange, QtCore.QEvent.Type.StyleChange):
            self._refit()

    def fitted_lines(self, width):
        """The lines this label shows at `width`, and whether any were cut."""
        self.ensurePolished()
        metrics = QtGui.QFontMetrics(self.font())

        lines = []
        current = ""
        for word in self._full_text.split():
            candidate = "{} {}".format(current, word) if current else word
            if not current or metrics.horizontalAdvance(candidate) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        cut = False
        if len(lines) > self._max_lines:
            lines = lines[:self._max_lines - 1] + [" ".join(lines[self._max_lines - 1:])]
            cut = True

        fitted = []
        for line in lines:
            elided = metrics.elidedText(line, QtCore.Qt.TextElideMode.ElideRight, width)
            cut = cut or elided != line
            fitted.append(elided)
        return fitted, cut

    def _refit(self):
        width = self.contentsRect().width()
        if width <= 0:
            if self.text() != self._full_text:
                super().setText(self._full_text)
            return

        lines, cut = self.fitted_lines(width)
        shown = "\n".join(lines)
        if shown != self.text():
            super().setText(shown)
            self.updateGeometry()
        self.setToolTip(self._full_text if cut else "")


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
            ret = "Jita"

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

        # Mapper configuration (upstream's MapperConfig/MapperRegistry stack;
        # NavProcessor rebuilds the registry from mapper_configs every fetch)
        self.mapper_configs: List[MapperConfig] = []
        self.mapper_states: Dict[str, StateMapper] = {}

        self.global_proxy = None
        # Monotonic timestamp of the last completed mapper fetch; drives the
        # pill tooltip and the stale-data hint. There is deliberately NO
        # recurring auto-refresh: hitting mapper servers while the user
        # isn't even looking is wasteful and rude. One fetch at startup,
        # manual refreshes after that.
        self._last_fetch_at = None

        self.state_eve_connection = StateEVEConnection(
            {"connected": False, "char_name": None, "char_id": 0, "error": None}
        )

        self.network_manager = QtNetwork.QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_portrait_loaded)

        # Create UI Elements (replaces setupUi)
        self._create_ui_elements()

        # Table configuration
        self.tableWidget_path.setColumnCount(5)
        self.tableWidget_path.setHorizontalHeaderLabels(
            [
                "System",
                "Cls",
                "Sec",
                "Instructions",
                "Additional information",
            ]
        )
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

        self.status_sources_widget.clicked.connect(self.btn_trip_config_clicked)
        self._update_sources_status()
        self._status_eve_connection_update()

        # Icons
        self.icon_wormhole = QtGui.QIcon(":/images/wh_icon.png")

        # Thread initial config
        Logger.register_thread(QtCore.QThread.currentThread(), "main")

        # NavProcessor thread
        self.worker_thread = QtCore.QThread()
        Logger.register_thread(self.worker_thread, "worker_thread / NavProcessor")
        self.nav_processor = NavProcessor(self.nav)
        self.nav_processor.moveToThread(self.worker_thread)
        self.nav_processor.finished.connect(self.worker_thread_done)
        # noinspection PyUnresolvedReferences
        self.worker_thread.started.connect(self.nav_processor.process)

        # Version check thread
        self.version_thread = QtCore.QThread()
        Logger.register_thread(self.version_thread, "version_thread / VersionCheck")
        self.version_check = VersionCheck()
        self.version_check.moveToThread(self.version_thread)
        self.version_check.finished.connect(self.version_check_done)
        # noinspection PyUnresolvedReferences
        self.version_thread.started.connect(self.version_check.process)
        self.start_version_check.connect(self.version_check.process)

        # Route thread
        self.route_thread = QtCore.QThread()
        Logger.register_thread(self.route_thread, "route_thread")
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
        # Try to resume a previous session via the OS keyring so the user
        # doesn't have to re-auth through the browser on every app start.
        # This is a no-op the first time the app ever runs (no stored token)
        # and on platforms without a working keyring backend.
        self.esip.try_silent_login()

        # Start version check
        self.version_thread.start()

        # One startup fetch when mappers are already configured, so a
        # returning user doesn't have to remember to click Refresh Mappers.
        # This is a single fetch, not a recurring auto-refresh.
        if any(cfg.enabled for cfg in self.mapper_configs):
            QtCore.QTimer.singleShot(1000, self._startup_fetch)

        # Paint everything in the active mode now (widgets built before the
        # saved mode was read used the default), and repaint on every change:
        # the toggle, or the OS switching while in Auto.
        theme.changed.connect(self._restyle)
        self._restyle()

        # Set default size to fit 1080p
        self.resize(1000, 800)

    def _create_ui_elements(self):
        """
        Instantiates all UI widgets programmatically, replacing the old .ui file.
        """
        # Navigation
        self.pushButton_player_location = QtWidgets.QPushButton("◎")
        self.pushButton_player_location.setFixedSize(42, 42)
        self.pushButton_player_location.setToolTip(
            "Use my current location as the source (requires EVE login)"
        )
        self.pushButton_player_location.setEnabled(False)

        self.lineEdit_set_dest = QtWidgets.QLineEdit()
        self.lineEdit_set_dest.setPlaceholderText("Select a route row or type a system")
        self.pushButton_set_dest = QtWidgets.QPushButton("Set in-game destination")
        self.pushButton_set_dest.setToolTip(
            "Set the EVE autopilot destination (requires EVE login)"
        )
        self.pushButton_set_dest.setEnabled(False)

        self.lineEdit_source = QtWidgets.QLineEdit()
        self.lineEdit_source.setPlaceholderText("Source system")
        self.lineEdit_destination = QtWidgets.QLineEdit()
        self.lineEdit_destination.setPlaceholderText("Destination system")

        self.pushButton_swap = QtWidgets.QPushButton("⇄")
        self.pushButton_swap.setFixedSize(42, 42)
        self.pushButton_swap.setToolTip("Swap source and destination")
        self.pushButton_swap.setObjectName("btn_glyph_swap")
        self.pushButton_player_location.setObjectName("btn_glyph_locate")

        self.pushButton_find_path = QtWidgets.QPushButton("Find path")
        self.pushButton_find_path.setMinimumHeight(42)
        # The stylesheet styles these by objectName (#pushButton_find_path
        # etc.); programmatic widgets don't get names automatically, so
        # without these calls the accent colors silently never apply.
        self.pushButton_find_path.setObjectName("pushButton_find_path")
        self.pushButton_reset = QtWidgets.QPushButton("Reset chain")
        self.pushButton_reset.setMinimumHeight(42)

        # Mappers: the status pill is both the health display and the entry
        # point to the Mappers dialog (there is no separate config button).
        self.status_sources_widget = ClickableLabel()
        self.status_sources_widget.setObjectName("status_pill")
        self.status_sources_widget.setToolTip("Click to configure mappers")
        # Appearance: one menu for light/dark mode and the corp brand pack.
        # Rebuilt each time it opens, so a just-imported pack is listed.
        self.pushButton_theme = QtWidgets.QPushButton("Appearance")
        self.pushButton_theme.setObjectName("pushButton_theme")
        self.menu_appearance = QtWidgets.QMenu(self.pushButton_theme)
        self.menu_appearance.aboutToShow.connect(self._build_appearance_menu)
        self.pushButton_theme.setMenu(self.menu_appearance)

        self.pushButton_trip_get = QtWidgets.QPushButton("Refresh Mappers")
        self.pushButton_trip_get.setObjectName("pushButton_trip_get")
        self.pushButton_trip_get.setEnabled(False)

        # Identity row (sidebar top). The identity block owns the whole EVE
        # session: the connection line (and, when logged out, the portrait)
        # is the login/logout control — there is no separate button.
        self.lbl_connection = ClickableLabel()

        # Transient toast replacing the old status-bar messages
        self.lbl_toast = QtWidgets.QLabel(self)
        self.lbl_toast.setObjectName("toast")
        self.lbl_toast.hide()

        # Restrictions
        self.comboBox_size = QtWidgets.QComboBox()
        self.comboBox_size.addItems(
            ["Frigate (S)", "Cruiser (M)", "Battleship (L)", "Capital (XL)", "No Wormholes"]
        )

        self.checkBox_eol = QtWidgets.QCheckBox("Ignore EOL wormholes")
        self.checkBox_masscrit = QtWidgets.QCheckBox("Ignore critical mass wormholes")
        self.checkBox_ignore_old = QtWidgets.QCheckBox("Ignore wormholes >")
        self.spinBox_hours = QtWidgets.QSpinBox()
        self.spinBox_hours.setRange(0, 48)
        self.spinBox_hours.setValue(16)
        self.spinBox_hours.setSuffix(" h")

        # Avoidance
        self.lineEdit_system_avoid_name = QtWidgets.QLineEdit()
        self.lineEdit_system_avoid_name.setPlaceholderText("System name")
        self.pushButton_system_avoid_add = QtWidgets.QPushButton("Add")
        self.pushButton_system_avoid_add.setProperty("compact", True)

        self.lineEdit_region_avoid_name = QtWidgets.QLineEdit()
        self.lineEdit_region_avoid_name.setPlaceholderText("Region name")
        self.pushButton_region_avoid_add = QtWidgets.QPushButton("Add")
        self.pushButton_region_avoid_add.setProperty("compact", True)

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
        # No painted grid: the cells' own padding and the row separators
        # from the stylesheet do the structural work.
        self.tableWidget_path.setShowGrid(False)
        self.tableWidget_path.setAlternatingRowColors(True)
        self.lineEdit_short_format = QtWidgets.QLineEdit()
        self.lineEdit_short_format.setReadOnly(True)
        self.lineEdit_short_format.setPlaceholderText("Short format route (click to copy)")

        self.pushButton_copy_clipboard = QtWidgets.QPushButton("Copy")
        self.pushButton_copy_clipboard.setToolTip("Copy route to clipboard")
        self.pushButton_copy_clipboard.setFixedWidth(60)
        self.pushButton_copy_clipboard.setProperty("compact", True)

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
        sidebar_container = QtWidgets.QScrollArea()
        sidebar_container.setObjectName("sidebar_container")
        sidebar_container.setWidgetResizable(True)
        sidebar_container.setFixedWidth(340)  # Account for scrollbar width
        sidebar_container.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        sidebar_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        sidebar = QtWidgets.QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(15)

        # Identity row: compact portrait + name + connection state. This is
        # the EVE connection status display — there is no status bar.
        identity_row = QtWidgets.QHBoxLayout()
        identity_row.setSpacing(12)
        self.lbl_portrait = ClickableLabel()
        self.lbl_portrait.setFixedSize(72, 72)
        self.lbl_portrait.setScaledContents(True)
        self.lbl_portrait.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_portrait.setStyleSheet(theme.qss("border: 1px solid @border; background-color: @field;"))
        # Connection state as a badge on the portrait corner, so the text
        # line stays flush-left with the name (no floating dot).
        self.lbl_status_badge = QtWidgets.QLabel(self.lbl_portrait)
        self.lbl_status_badge.setFixedSize(16, 16)
        self.lbl_status_badge.move(58, 58)
        identity_row.addWidget(self.lbl_portrait)

        identity_col = QtWidgets.QVBoxLayout()
        identity_col.setSpacing(3)
        lbl_header = NameLabel("DAYTRIPPER")
        lbl_header.setObjectName("sidebar_header")
        identity_col.addWidget(lbl_header)
        self.lbl_header = lbl_header
        self.lbl_connection.setStyleSheet(theme.qss("color: @text_faint; font-size: 11px;"))
        identity_col.addWidget(self.lbl_connection)
        # The column takes all remaining width (no trailing stretch), so the
        # name label knows exactly how much room it has to wrap into.
        identity_row.addLayout(identity_col, 1)
        sidebar_layout.addLayout(identity_row)

        # Restrictions Group (Navigation lives in the route bar, not here)
        sidebar_layout.addWidget(self._setup_restrictions_group())

        # 3. Security & Avoidance
        sidebar_layout.addWidget(self._setup_security_group())
        sidebar_layout.addWidget(self._setup_avoidance_group())

        sidebar_layout.addStretch()
        sidebar_container.setWidget(sidebar)

        # --- Right Main Area ---
        content = QtWidgets.QWidget()
        content.setObjectName("main_area")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Action row: mapper status pill (clickable -> Mappers dialog) left,
        # fetch + login actions right.
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addWidget(self.status_sources_widget)
        top_bar.addStretch()
        top_bar.addWidget(self.pushButton_theme)
        top_bar.addWidget(self.pushButton_trip_get)
        content_layout.addLayout(top_bar)

        # Hero route bar: the thing you touch every session.
        content_layout.addWidget(self._setup_route_bar())
        self.progressBar_route = QtWidgets.QProgressBar()
        self.progressBar_route.setRange(0, 0)
        self.progressBar_route.setTextVisible(False)
        self.progressBar_route.setVisible(False)
        self.progressBar_route.setFixedHeight(5)
        content_layout.addWidget(self.progressBar_route)

        # Route Results Panel
        results_group = QtWidgets.QGroupBox("ROUTE RESULTS")
        results_layout = QtWidgets.QVBoxLayout(results_group)
        results_layout.setContentsMargins(10, 15, 10, 10)
        results_layout.setSpacing(10)

        results_layout.addWidget(self.label_status)
        results_layout.addWidget(self.tableWidget_path)

        # In-game autopilot row below the table: the field fills from the
        # selected route row (or can be typed into), the button pushes it
        # to the EVE client.
        row_table_actions = QtWidgets.QHBoxLayout()
        self.lineEdit_set_dest.setMaximumWidth(260)
        row_table_actions.addWidget(self.lineEdit_set_dest)
        row_table_actions.addWidget(self.pushButton_set_dest)
        row_table_actions.addStretch()

        # Copy Table Button (reusing existing logic)
        self.pushButton_copy_table = QtWidgets.QPushButton("Copy Table")
        self.pushButton_copy_table.clicked.connect(self.copy_table_to_clipboard)
        row_table_actions.addWidget(self.pushButton_copy_table)

        results_layout.addLayout(row_table_actions)
        content_layout.addWidget(results_group)

        # Copy-Paste Info Panel
        copy_panel = QtWidgets.QGroupBox("FC, PLEASE HELP!")
        copy_layout = QtWidgets.QHBoxLayout(copy_panel)
        copy_layout.setContentsMargins(5, 15, 5, 5)
        copy_layout.setSpacing(0)

        copy_layout.addWidget(self.lineEdit_short_format)
        copy_layout.addWidget(self.pushButton_copy_clipboard)

        content_layout.addWidget(copy_panel)

        main_layout.addWidget(sidebar_container)
        main_layout.addWidget(content)
        self.setCentralWidget(new_central)

    def _apply_styles(self):
        self.setStyleSheet(theme.qss(MAIN_QSS))

    THEME_LABELS = {"system": "◐  Auto", "light": "☀  Light", "dark": "☾  Dark"}
    THEME_NAMES = {"system": "Auto (follows your system)", "light": "Light", "dark": "Dark"}
    DEFAULT_BRAND_NAME = "Short Circuit"

    @staticmethod
    def _menu_heading(menu, text):
        # QMenu.addSection draws a bare line under Fusion, so headings are
        # disabled actions instead: visible, but not clickable.
        if menu.actions():
            menu.addSeparator()
        heading = menu.addAction(text.upper())
        heading.setEnabled(False)
        font = heading.font()
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 0.85)
        heading.setFont(font)

    def _build_appearance_menu(self):
        menu = self.menu_appearance
        menu.clear()

        self._menu_heading(menu, "Mode")
        modes = QtGui.QActionGroup(menu)
        for mode in ("system", "light", "dark"):
            action = menu.addAction(self.THEME_LABELS[mode])
            action.setCheckable(True)
            action.setChecked(theme.mode == mode)
            action.setActionGroup(modes)
            action.triggered.connect(partial(self._choose_mode, mode))

        self._menu_heading(menu, "Brand")
        current = (theme.brand or {}).get("slug")
        group = QtGui.QActionGroup(menu)
        choices = [(None, self.DEFAULT_BRAND_NAME)] + [
            (pack["slug"], pack["name"]) for pack in brands.list_packs()
        ]
        for slug, name in choices:
            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(slug == current)
            action.setActionGroup(group)
            action.triggered.connect(partial(self._choose_brand, slug))

        menu.addSeparator()
        menu.addAction("Import brand pack…").triggered.connect(self._import_brand)
        pack = brands.find_pack(current) if current else None
        if pack and pack["imported"]:
            menu.addAction("Remove {}".format(pack["name"])).triggered.connect(
                partial(self._remove_brand, current)
            )

    def _choose_mode(self, mode, _checked=False):
        theme.set_mode(mode)
        self.settings.setValue("theme_mode", mode)
        # set_mode only signals when the colors actually change (Auto ->
        # Light on a light OS doesn't), but the button always must.
        self._update_theme_button()

    def _choose_brand(self, slug, _checked=False):
        pack = brands.find_pack(slug) if slug else None
        theme.set_brand(brands.load_pack(pack["path"]) if pack else None)
        self.settings.setValue("brand", slug or "")
        self._update_theme_button()

    @QtCore.Slot()
    def _import_brand(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose the brand pack folder (it contains brand.json)", os.path.expanduser("~")
        )
        if not folder:
            return
        try:
            slug = brands.import_pack(folder)
        except (ValueError, OSError) as e:
            self._message_box("Import brand pack", str(e))
            return
        self._choose_brand(slug)
        self._toast("Brand pack imported: {}".format(theme.brand["name"] if theme.brand else slug))

    def _remove_brand(self, slug, _checked=False):
        pack = brands.find_pack(slug)
        if not pack:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Remove brand pack",
            "Remove the {} brand pack from this computer? You can import it again later.".format(
                pack["name"]
            ),
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        brands.remove_pack(slug)
        self._choose_brand(None)

    def _update_theme_button(self):
        brand = theme.brand["name"] if theme.brand else self.DEFAULT_BRAND_NAME
        self.pushButton_theme.setToolTip(
            "Mode: {} · Brand: {}".format(self.THEME_NAMES[theme.mode], brand)
        )

    def _restore_brand(self):
        slug = str(self.settings.value("brand", "") or "")
        pack = brands.find_pack(slug) if slug else None
        if slug and not pack:
            Logger.warning("Saved brand pack '{}' is gone; using the default look".format(slug))
        theme.set_brand(brands.load_pack(pack["path"]) if pack else None)

    @QtCore.Slot()
    def _restyle(self):
        """Repaint everything that carries a color for the current mode.
        Pure painting: no network, no state changes."""
        self._apply_styles()
        self._style_security_rows()
        self._render_identity()
        if getattr(self, "_pill_args", None):
            self._set_pill(*self._pill_args)
        state = getattr(self, "_path_state", None)
        if state and state[0] == "route":
            self._render_route_summary(state[1])
        elif state:
            MainWindow._label_message(self.label_status, state[1], state[2])
        if getattr(self, "_last_route", None):
            self.add_data_to_table(self._last_route)
            self.table_item_selection_changed()
        self._update_theme_button()

    def _style_security_rows(self):
        """Each security row's label, filled bar and handle carry that
        row's data color (HS green, LS yellow, NS red, WH blue)."""
        for lbl, slider, token in self._security_rows:
            color = theme[token]
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            slider.setStyleSheet(
                f"QSlider::sub-page:horizontal {{ background: {color}; border: 1px solid {color}; border-radius: 3px; }}"
                f" QSlider::handle:horizontal {{ background: {color}; border: 1px solid {color}; }}"
            )

    def _setup_security_group(self):
        group = QtWidgets.QGroupBox("SECURITY PRIORITIZATION")
        group.setCheckable(True)
        layout = QtWidgets.QVBoxLayout(group)
        layout.setSpacing(5)

        self._security_rows = []

        def create_slider(label_text, attr_name, token):
            row = QtWidgets.QHBoxLayout()

            lbl = QtWidgets.QLabel(label_text)
            lbl.setFixedWidth(30)

            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(1, 100)
            self._security_rows.append((lbl, slider, token))

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

        create_slider("HS", "slider_prio_hs", "sec_hs")
        create_slider("LS", "slider_prio_ls", "sec_ls")
        create_slider("NS", "slider_prio_ns", "sec_ns")
        create_slider("WH", "slider_prio_wh", "sec_wh")
        self._style_security_rows()

        # Replace the old groupbox reference so isChecked() works on the new one
        self.groupBox_security = group
        return group

    def _setup_avoidance_group(self):
        group = QtWidgets.QGroupBox("AVOIDANCE LIST")
        group.setCheckable(True)
        # Preserve checked state if possible
        if hasattr(self, "groupBox_avoidance"):
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

    def _setup_route_bar(self):
        bar = QtWidgets.QWidget()
        bar.setObjectName("route_bar")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        layout.addWidget(self.pushButton_player_location)
        layout.addWidget(self.lineEdit_source, 1)
        layout.addWidget(self.pushButton_swap)
        layout.addWidget(self.lineEdit_destination, 1)
        layout.addWidget(self.pushButton_find_path)
        layout.addWidget(self.pushButton_reset)

        return bar

    def _setup_restrictions_group(self):
        group = QtWidgets.QGroupBox("WORMHOLE RESTRICTIONS")
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
            "{} v{} ({})".format(
                __appname__,
                __version__,
                last_update,
            )
        )
        self._path_message("Type a destination and press Find path", MessageType.INFO)
        self._avoid_message("", MessageType.OK)
        self.lineEdit_source.setFocus()
        self.lineEdit_short_format.mousePressEvent = partial(MainWindow.short_format_click, self)

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
            completer.setModelSorting(QtWidgets.QCompleter.CaseInsensitivelySortedModel)
            line_edit_field.setCompleter(completer)

        region_list = self.nav.eve_db.region_name_list()
        region_list.sort(key=str.lower)
        completer = QtWidgets.QCompleter(region_list, self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setModelSorting(QtWidgets.QCompleter.CaseInsensitivelySortedModel)
        completer.setFilterMode(QtCore.Qt.MatchContains)
        self.lineEdit_region_avoid_name.setCompleter(completer)

        # Signals
        self.lbl_connection.clicked.connect(self.btn_eve_login_clicked)
        self.lbl_portrait.clicked.connect(self._portrait_clicked)
        self.pushButton_player_location.clicked.connect(self.btn_player_location_clicked)
        self.pushButton_find_path.clicked.connect(self.btn_find_path_clicked)
        self.pushButton_trip_get.clicked.connect(self.btn_trip_get_clicked)
        self.pushButton_system_avoid_add.clicked.connect(self.btn_system_avoid_add_clicked)
        self.pushButton_region_avoid_add.clicked.connect(self.btn_region_avoid_add_clicked)
        self.pushButton_avoid_delete.clicked.connect(self.btn_avoid_delete_clicked)
        self.pushButton_avoid_clear.clicked.connect(self.btn_avoid_clear_clicked)
        self.pushButton_set_dest.clicked.connect(self.btn_set_dest_clicked)
        self.pushButton_reset.clicked.connect(self.btn_reset_clicked)
        self.lineEdit_source.returnPressed.connect(self.line_edit_source_return)
        self.lineEdit_destination.returnPressed.connect(self.line_edit_destination_return)
        self.lineEdit_system_avoid_name.returnPressed.connect(
            self.line_edit_system_avoid_name_return
        )
        self.lineEdit_region_avoid_name.returnPressed.connect(
            self.line_edit_region_avoid_name_return
        )

        self.pushButton_copy_clipboard.clicked.connect(self.short_format_click_btn)
        self.pushButton_swap.clicked.connect(self.btn_swap_clicked)
        self.lineEdit_set_dest.returnPressed.connect(self.btn_set_dest_clicked)
        self.tableWidget_path.itemSelectionChanged.connect(self.table_item_selection_changed)

        # Tab order
        self.setTabOrder(self.lineEdit_source, self.lineEdit_destination)
        self.setTabOrder(self.lineEdit_destination, self.pushButton_find_path)
        self.setTabOrder(self.pushButton_find_path, self.pushButton_reset)

        # Allow Enter key to trigger button when focused
        self.pushButton_find_path.setAutoDefault(True)

    def read_settings_general(self):
        self.global_proxy = self.settings.value("proxy", "")
        theme.set_mode(str(self.settings.value("theme_mode", "system")))
        self._restore_brand()
        # Mapper configs: migrate_legacy handles both historic layouts (flat
        # MainWindow/tripwire_* keys and the fork's grouped Tripwire/* keys),
        # so the fork-era migration shim is gone.
        migrated = migrate_legacy(self.settings)
        if migrated is not None:
            self.mapper_configs = migrated
        else:
            loaded = load_configs(self.settings)
            self.mapper_configs = loaded if loaded else default_configs()
        self.mapper_states = {
            cfg.name: StateMapper({"connections": 0, "error": None})
            for cfg in self.mapper_configs
        }

        if any(cfg.enabled for cfg in self.mapper_configs):
            self.pushButton_trip_get.setEnabled(True)

    def read_settings(self):
        self.read_settings_general()

        self.settings.beginGroup("MainWindow")

        # Window state
        win_geometry = self.settings.value("win_geometry")
        if win_geometry:
            self.restoreGeometry(win_geometry)
        win_state = self.settings.value("win_state")
        if win_state:
            self.restoreState(win_state)
        for col_idx, column_width in enumerate(
            self.settings.value("table_widths", "110,75,75,250,200").split(",")
        ):
            if col_idx < self.tableWidget_path.columnCount():
                self.tableWidget_path.setColumnWidth(col_idx, int(column_width))

        # Avoidance list
        self.groupBox_avoidance.setChecked(
            self.settings.value("avoidance_enabled", "false") == "true"
        )
        for entity in self.settings.value("avoidance_list", "").split(","):
            if entity != "":
                self._avoid_entity_name(entity, announce=False)

        # Restrictions
        self.comboBox_size.setCurrentIndex(int(self.settings.value("restrictions_whsize", "0")))
        self.checkBox_eol.setChecked(self.settings.value("restriction_eol", "false") == "true")
        self.checkBox_masscrit.setChecked(
            self.settings.value("restriction_masscrit", "false") == "true"
        )
        self.checkBox_ignore_old.setChecked(
            self.settings.value("restriction_ignore_old", "false") == "true"
        )
        self.spinBox_hours.setValue(int(float(self.settings.value("restriction_hours", "16.0"))))

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

    def write_settings_general(self):
        self.settings.setValue("proxy", getattr(self, "global_proxy", ""))
        save_configs(self.settings, self.mapper_configs)

    def write_settings(self):
        self.write_settings_general()

        self.settings.beginGroup("MainWindow")

        # Window state
        self.settings.setValue("win_geometry", self.saveGeometry())
        self.settings.setValue("win_state", self.saveState())

        widths = [
            str(self.tableWidget_path.columnWidth(i))
            for i in range(self.tableWidget_path.columnCount())
        ]
        self.settings.setValue("table_widths", ",".join(widths))

        # Avoidance list
        self.settings.setValue("avoidance_enabled", self.groupBox_avoidance.isChecked())
        avoidance_list_string = ",".join(self.avoidance_list())
        self.settings.setValue("avoidance_list", avoidance_list_string)

        # Restrictions
        self.settings.setValue("restrictions_whsize", self.comboBox_size.currentIndex())
        self.settings.setValue("restriction_eol", self.checkBox_eol.isChecked())
        self.settings.setValue("restriction_masscrit", self.checkBox_masscrit.isChecked())
        self.settings.setValue("restriction_ignore_old", self.checkBox_ignore_old.isChecked())
        self.settings.setValue("restriction_hours", self.spinBox_hours.value())

        # Security prioritization
        self.settings.setValue("security_enabled", self.groupBox_security.isChecked())
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
            label.setStyleSheet(theme.qss("QLabel {color: @status_ok;}"))
        elif message_type == MessageType.ERROR:
            label.setStyleSheet(theme.qss("QLabel {color: @status_error;}"))
        else:
            label.setStyleSheet(theme.qss("QLabel {color: @text_secondary;}"))
        label.setText(message)

    def _avoid_message(self, message, message_type):
        self._toast(message)

    def _path_message(self, message, message_type):
        # Remembered so a theme change can repaint it in the new colors.
        self._path_state = ("message", message, message_type)
        MainWindow._label_message(self.label_status, message, message_type)

    def _toast(self, message, duration_ms=3500):
        """Transient bottom-right notice; replaces the old status-bar
        showMessage calls now that there is no status bar."""
        if not message:
            return
        self.lbl_toast.setText(message)
        self.lbl_toast.adjustSize()
        self._position_toast()
        self.lbl_toast.show()
        self.lbl_toast.raise_()
        QtCore.QTimer.singleShot(duration_ms, self.lbl_toast.hide)

    def _position_toast(self):
        margin = 24
        self.lbl_toast.move(
            self.width() - self.lbl_toast.width() - margin,
            self.height() - self.lbl_toast.height() - margin,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.lbl_toast.isVisible():
            self._position_toast()

    def avoidance_enabled(self) -> bool:
        return self.groupBox_avoidance.isChecked()

    def avoidance_list(self) -> List[str]:
        items: List[str] = []
        for idx in range(self.listWidget_avoid.count()):
            item: QtWidgets.QListWidgetItem = self.listWidget_avoid.item(idx)
            items.append(item.text())
        return items

    def _avoid_entity_name(self, name, announce=True):
        """Add a system or region to the avoidance list. `announce` toasts
        the result; restoring saved entries at startup passes False."""
        if not name:
            if announce:
                self._avoid_message("Avoidance list: invalid name :(", MessageType.ERROR)
            return

        if name in self.avoidance_list():
            if announce:
                self._avoid_message(
                    "Avoidance list: {} is already in the list!".format(name), MessageType.ERROR
                )
            return

        QtWidgets.QListWidgetItem(name, self.listWidget_avoid)
        if announce:
            self._avoid_message("Avoidance list: {} added".format(name), MessageType.OK)

    def avoid_system(self):
        sys_name = self.nav.eve_db.normalize_name(self.lineEdit_system_avoid_name.text())
        self._avoid_entity_name(sys_name)

    def avoid_region(self):
        region_name = self.nav.eve_db.normalize_region_name(self.lineEdit_region_avoid_name.text())
        self._avoid_entity_name(region_name)

    @staticmethod
    def get_system_class_color(sclass):
        if sclass.startswith("C") or sclass == "WH":
            return theme.color("route_wh")

        return theme.color({
            "HS": "route_hs",
            "LS": "route_ls",
            "NS": "route_ns",
            "▲": "route_ns",
            "Z": "route_ns",
        }.get(sclass, "route_other"))

    def add_data_to_table(self, route):
        self.tableWidget_path.setRowCount(len(route))

        for route_step_id, route_step in enumerate(route):
            color = self.get_system_class_color(route_step["class"])

            route_step["security"] = round(route_step["security"], 1)

            ui_col_id = 0
            for col_id in [
                "name",
                "class",
                "security",
                "path_action",
                "path_info",
            ]:
                text = str(route_step.get(col_id, ""))
                item = QtWidgets.QTableWidgetItem(text)

                if col_id in ["class", "security"]:
                    item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    item.setForeground(color)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                if col_id == "path_action":
                    if "wormhole" in text:
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
        age_threshold = float("inf")

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
        self._last_route = None
        self.tableWidget_path.setRowCount(0)
        self.lineEdit_short_format.setText("")

    def find_path(self):
        source_sys_name = self.nav.eve_db.normalize_name(self.lineEdit_source.text().strip())
        dest_sys_name = self.nav.eve_db.normalize_name(self.lineEdit_destination.text().strip())

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

        # Politeness over automation: we never refetch mapper data behind
        # the user's back (and a just-in-time fetch here would make every
        # route feel slow). Instead, routing on stale data earns a hint.
        if (
            self._last_fetch_at is not None
            and time.monotonic() - self._last_fetch_at > 15 * 60
        ):
            minutes = int((time.monotonic() - self._last_fetch_at) / 60)
            self._toast(
                "Wormhole data is {} min old — Refresh Mappers for the current chain".format(minutes),
                duration_ms=5000,
            )

    @QtCore.Slot(list, str)
    def route_result_handler(self, route, short_format):
        self.pushButton_find_path.setEnabled(True)
        self.progressBar_route.setVisible(False)

        if not route:
            self._clear_results()
            self._path_message("No path found between the solar systems.", MessageType.ERROR)
            return

        route_length = len(route)
        if route_length == 1:
            self._path_message("Set the same source and destination :P", MessageType.OK)
        else:
            self._render_route_summary(route)

        self._last_route = route
        self.add_data_to_table(route)
        self.lineEdit_short_format.setText(short_format)

    def _render_route_summary(self, route):
        """'3 JUMPS FROM PERIMETER TO 1DQ1-A', endpoints in their class colors."""
        self._path_state = ("route", route)
        source_color = self.get_system_class_color(route[0]["class"]).name()
        dest_color = self.get_system_class_color(route[-1]["class"]).name()

        jumps = len(route) - 1
        self.label_status.setText(
            '<span style="font-size: 20pt; color: {}">{}</span> {} FROM <span style="color:{}">{}</span> TO <span style="color:{}">{}</span>'.format(
                theme["jump_count"],
                jumps,
                "JUMP" if jumps == 1 else "JUMPS",
                source_color,
                route[0]["name"].upper(),
                dest_color,
                route[-1]["name"].upper(),
            )
        )
        self.label_status.setStyleSheet(
            theme.qss("QLabel {color: @text_strong; font-weight: bold; font-size: 12pt;}")
        )

    def short_format_click(self, event):
        event.accept()
        if not self.lineEdit_short_format.text():
            return
        self.lineEdit_short_format.selectAll()
        self.lineEdit_short_format.copy()
        self._toast("Copied travel info to clipboard!")

    def short_format_click_btn(self):
        if not self.lineEdit_short_format.text():
            return
        self.lineEdit_short_format.selectAll()
        self.lineEdit_short_format.copy()
        self._toast("Copied travel info to clipboard!")

    @QtCore.Slot()
    def copy_table_to_clipboard(self):
        if self.tableWidget_path.rowCount() == 0:
            self._toast("No route to copy!")
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
        self._toast("Route table copied to clipboard!")

    def _status_eve_connection_update(self):
        """The identity row IS the EVE connection status display."""
        self._render_identity()
        if self.state_eve_connection["connected"]:
            self._load_portrait(self.state_eve_connection["char_id"])
        elif not self.state_eve_connection["error"]:
            self._load_portrait(1)

    def _render_identity(self):
        """Paint the identity row for the current state and theme. No network:
        a theme change re-runs this without refetching the portrait."""
        t = theme.tokens()
        sep = '<span style="color:{}"> · </span>'.format(t["text_faint"])
        self.lbl_portrait.setStyleSheet(
            theme.qss("border: 1px solid @border; background-color: @field;")
        )

        if self.state_eve_connection["connected"]:
            self.pushButton_player_location.setEnabled(True)
            self.pushButton_set_dest.setEnabled(True)

            if self.state_eve_connection["char_name"]:
                self.lbl_header.setText(self.state_eve_connection["char_name"].upper())
                self.lbl_header.setStyleSheet(
                    theme.qss("color: @link; font-weight: bold; font-size: 14px;")
                )
            self.lbl_connection.setText(
                '<span style="color:{}">Connected</span>{}<span style="color:{}">Log out</span>'.format(
                    t["status_ok"], sep, t["link"]
                )
            )
            self._set_status_badge(t["status_ok"])
            self.lbl_portrait.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self.lbl_portrait.setToolTip(
                "Logged in as {}".format(self.state_eve_connection["char_name"])
            )
            return

        if self.state_eve_connection["error"]:
            self.lbl_connection.setText(
                '<span style="color:{}">{}</span>{}<span style="color:{}">Retry</span>'.format(
                    t["status_error"], self.state_eve_connection["error"], sep, t["link"]
                )
            )
            self._set_status_badge(t["status_error"])
            return

        self.pushButton_player_location.setEnabled(False)
        self.pushButton_set_dest.setEnabled(False)

        # Logged out, the letterhead is the corp's name (or the app's own).
        self.lbl_header.setText(theme.brand["short"].upper() if theme.brand else "DAYTRIPPER")
        self.lbl_header.setStyleSheet(theme.qss("color: @text; font-weight: bold; font-size: 14px;"))
        self.lbl_connection.setText(
            '<span style="color:{}">Log in with EvE</span>'.format(t["link"])
        )
        self._set_status_badge(t["text_faint"])
        self.lbl_portrait.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.lbl_portrait.setToolTip("Log in with EVE")

    @QtCore.Slot()
    def _portrait_clicked(self):
        # The portrait is a login affordance only while logged out; clicking
        # your own face should never log you out.
        if not self.state_eve_connection["connected"]:
            self.btn_eve_login_clicked()

    def _set_status_badge(self, color):
        self.lbl_status_badge.setStyleSheet(
            "background-color: {}; border: 2px solid {}; border-radius: 8px;".format(
                color, theme["panel"]
            )
        )

    def _update_sources_status(self):
        total_connections = 0
        active_count = 0
        has_errors = False

        for cfg in self.mapper_configs:
            if not cfg.enabled:
                continue
            active_count += 1
            state = self.mapper_states.get(cfg.name)
            if state is None:
                continue
            if state["error"]:
                has_errors = True
            else:
                total_connections += state["connections"]

        mapper_word = "mapper" if active_count == 1 else "mappers"
        if active_count > 0 and not has_errors and self._last_fetch_at is None:
            # Before the first fetch "0 connections" would read as a problem.
            self._set_pill("text_secondary", f"{active_count} {mapper_word} · awaiting first fetch")
        elif has_errors:
            self._set_pill(
                "status_error",
                f"<b>{active_count} {mapper_word} · {total_connections} connections · errors</b>",
            )
        elif active_count > 0:
            self._set_pill(
                "status_ok", f"{active_count} {mapper_word} · {total_connections} connections"
            )
        else:
            self._set_pill("text_secondary", "No mappers", action="Add one")

    def _set_pill(self, color_token, status_html, action="Manage"):
        """Status pill content: colored status text plus a link-colored
        action word so the pill reads as clickable at a glance."""
        # Remembered so a theme change mid-fetch repaints "Refreshing…",
        # not a stale count.
        self._pill_args = (color_token, status_html, action)
        t = theme.tokens()
        self.status_sources_widget.setText(
            '<span style="color:{c}">●&nbsp;&nbsp;{s}</span>'
            '<span style="color:{f}">&nbsp;&nbsp;·&nbsp;&nbsp;</span>'
            '<span style="color:{l}">{a} ⚙</span>'.format(
                c=t[color_token], s=status_html, f=t["text_faint"], l=t["link"], a=action
            )
        )

    @QtCore.Slot(bool, str)
    def login_handler(self, is_ok, char_name):
        # Upstream's signal carries (is_ok, char_name); the char_id the
        # portrait needs lives on the ESI object itself.
        char_id = int(self.esip.esi.char_id or 0) if is_ok else 0

        self.state_eve_connection["connected"] = is_ok
        self.state_eve_connection["char_name"] = char_name
        self.state_eve_connection["char_id"] = char_id
        self.state_eve_connection["error"] = "ESI error" if not is_ok else None

        Logger.info(f"Login handler: ok={is_ok}, name={char_name}, id={char_id}")
        self._status_eve_connection_update()

        # Pre-fill the source with the pilot's location so the common flow
        # after login is just: type destination, Find path. Runs silently —
        # failures don't interrupt, and a source the user already typed is
        # never overwritten (see location_handler).
        if is_ok:
            self._auto_location = True
            self.esip.get_location()

    @QtCore.Slot()
    def logout_handler(self):
        self.state_eve_connection["connected"] = False
        self.state_eve_connection["char_name"] = None
        self.state_eve_connection["char_id"] = 0
        self.state_eve_connection["error"] = None
        self._status_eve_connection_update()

    @QtCore.Slot(str)
    def location_handler(self, location):
        auto = getattr(self, "_auto_location", False)
        self._auto_location = False

        if location:
            if auto and self.lineEdit_source.text().strip():
                # Don't clobber a source the user already typed.
                pass
            else:
                self.lineEdit_source.setText(location)
        elif not auto:
            self._message_box(
                "Player location", "Unable to get location (character not online or ESI error)"
            )
        self.pushButton_player_location.setEnabled(True)

    @QtCore.Slot(bool)
    def destination_handler(self, response):
        if not response:
            self._message_box("Player destination", "ESI error when trying to set destination")
        self.pushButton_set_dest.setEnabled(True)

    @QtCore.Slot(dict)
    def worker_thread_done(self, results):
        self.worker_thread.quit()

        # wait for thread to finish
        while self.worker_thread.isRunning():
            time.sleep(0.01)

        for name, count in results.items():
            if count < 0:
                self.mapper_states[name] = StateMapper({"connections": 0, "error": "error"})
            else:
                self.mapper_states[name] = StateMapper({"connections": count, "error": None})
        self._last_fetch_at = time.monotonic()
        self.status_sources_widget.setToolTip(
            "Last fetch: {} — click to configure mappers".format(time.strftime("%H:%M"))
        )
        self._update_sources_status()

        # Empty-state guidance: once connections are in and no route is
        # shown yet, tell the user the one step that remains.
        if self.tableWidget_path.rowCount() == 0:
            loaded = sum(
                s["connections"] for s in self.mapper_states.values() if not s["error"]
            )
            if loaded > 0:
                self._path_message(
                    "{} connections loaded — type a destination and press Find path".format(loaded),
                    MessageType.OK,
                )

        has_active = any(cfg.enabled for cfg in self.mapper_configs)
        self.pushButton_trip_get.setEnabled(has_active)
        self.pushButton_find_path.setEnabled(True)

    @QtCore.Slot()
    def btn_eve_login_clicked(self):
        try:
            if not self.state_eve_connection["connected"]:
                self.esip.login()
            else:
                self.esip.logout()
        except Exception as e:
            Logger.error(f"EVE Login error: {e}")
            self._message_box("Login Error", f"Unable to initiate login: {e}")

    @QtCore.Slot()
    def btn_player_location_clicked(self):
        self._auto_location = False
        self.pushButton_player_location.setEnabled(False)
        self.esip.get_location()

    @QtCore.Slot()
    def btn_set_dest_clicked(self):
        if self.pushButton_set_dest.isEnabled():
            dest_sys_name = self.nav.eve_db.normalize_name(self.lineEdit_set_dest.text().strip())
            sys_id = self.nav.eve_db.name2id(dest_sys_name)
            if sys_id:
                self.pushButton_set_dest.setEnabled(False)
                self.esip.set_destination(sys_id)
            else:
                if self.lineEdit_set_dest.text().strip() == "":
                    msg_txt = "No system name give as input"
                else:
                    msg_txt = "Invalid system name: '{}'".format(self.lineEdit_set_dest.text())
                self._message_box("Player destination", msg_txt)

    @QtCore.Slot()
    def btn_find_path_clicked(self):
        self.find_path()

    @QtCore.Slot()
    def btn_swap_clicked(self):
        source_text = self.lineEdit_source.text()
        self.lineEdit_source.setText(self.lineEdit_destination.text())
        self.lineEdit_destination.setText(source_text)

    @QtCore.Slot()
    def _startup_fetch(self):
        if not self.worker_thread.isRunning():
            self._start_worker()

    @QtCore.Slot()
    def btn_trip_config_clicked(self):
        dialog = MappersDialog(self.mapper_configs, self.global_proxy, parent=self)
        if not dialog.exec():
            return

        self.mapper_configs = dialog.configs
        self.global_proxy = dialog.proxy

        # Preserve per-mapper state across renames/removals by keeping entries
        # only for configs that still exist; add fresh empty state for new ones.
        new_states: Dict[str, StateMapper] = {}
        for cfg in self.mapper_configs:
            new_states[cfg.name] = self.mapper_states.get(
                cfg.name, StateMapper({"connections": 0, "error": None})
            )
        self.mapper_states = new_states

        save_configs(self.settings, self.mapper_configs)
        self.settings.setValue("proxy", self.global_proxy)

        self._update_sources_status()

        has_active = any(cfg.enabled for cfg in self.mapper_configs)
        self.pushButton_trip_get.setEnabled(has_active and not self.worker_thread.isRunning())

    @QtCore.Slot()
    def btn_trip_get_clicked(self):
        self._start_worker()

    def _start_worker(self):
        if not self.worker_thread.isRunning():
            self.pushButton_trip_get.setEnabled(False)
            self.pushButton_find_path.setEnabled(False)
            self._set_pill("text_secondary", "Refreshing mappers…")
            self.worker_thread.start()
        else:
            self._update_sources_status()
            self._message_box("Mappers", "A mapper refresh is already running.")

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
        msg_box.setText("Are you sure you want to clear all Map Source data?")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg_box.setDefaultButton(QtWidgets.QMessageBox.No)
        ret = msg_box.exec()

        if ret == QtWidgets.QMessageBox.Yes:
            self.nav.reset_chain()
            self.mapper_states = {
                cfg.name: StateMapper({"connections": 0, "error": None})
                for cfg in self.mapper_configs
            }
            self._update_sources_status()

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

    def _table_style(self, pick_token):
        self.tableWidget_path.setStyleSheet(
            theme.qss(
                "selection-color: @on_pick; selection-background-color: @{};".format(pick_token)
            )
        )

    @QtCore.Slot()
    def table_item_selection_changed(self):
        selection = self.tableWidget_path.selectedItems()
        if selection:
            sys_class = selection[1].text()
            if sys_class == "HS":
                self._table_style("pick_hs")
            elif sys_class == "LS":
                self._table_style("pick_ls")
            elif sys_class == "NS":
                self._table_style("pick_ns")
            else:
                self._table_style("pick_wh")

            self.lineEdit_set_dest.setText(selection[0].text())

    @QtCore.Slot(str)
    def version_check_done(self, latest):
        if not latest:
            return

        latest = json.loads(latest)
        version = latest["tag_name"].split("v")[-1]
        changelog = latest.get("body") or "No changelog provided."
        if len(changelog) > 1200:
            changelog = changelog[0:1200].split(" ")
            del changelog[-1]
            changelog = " ".join(changelog)

        version_box = QtWidgets.QMessageBox(self)
        version_box.setWindowTitle("New version available!")
        version_box.setText(
            "Your version: v{} ({}).\nGitHub latest release: v{} ({}).\n\n{}".format(
                __version__,
                last_update,
                version,
                latest["published_at"],
                changelog,
            )
        )
        version_box.addButton("Download now", QtWidgets.QMessageBox.AcceptRole)
        version_box.addButton("Remind me later", QtWidgets.QMessageBox.RejectRole)
        ret = version_box.exec()

        if ret != QtWidgets.QMessageBox.AcceptRole:
            return

        url_to_open = QtCore.QUrl(
            f"https://github.com/mogglemoss/shortcircuit/releases/tag/{latest['tag_name']}"
        )

        if sys.platform == "linux":
            import subprocess

            env = os.environ.copy()
            env.pop("LD_LIBRARY_PATH", None)
            try:
                subprocess.Popen(["xdg-open", url_to_open.toString()], env=env)
            except OSError:
                webbrowser.open(url_to_open.toString())
        else:
            QtGui.QDesktopServices.openUrl(url_to_open)

    def _load_portrait(self, char_id):
        url = f"https://images.evetech.net/characters/{char_id}/portrait?size=128"
        Logger.info(f"Portrait request: char_id={char_id}, url={url}")
        self.network_manager.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))

    def _on_portrait_loaded(self, reply):
        url = reply.url().toString()
        if reply.error() == QtNetwork.QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QtGui.QPixmap()
            ok = pixmap.loadFromData(data)
            Logger.info(f"Portrait response: url={url}, data_size={len(data)}, decode_ok={ok}")
            if ok:
                self.lbl_portrait.setPixmap(pixmap)
            else:
                Logger.error(f"Portrait image decode failed for {url}")
        else:
            Logger.error(f"Portrait network error: {reply.errorString()}, url={url}")
        reply.deleteLater()

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

    # Patch QDesktopServices.openUrl on Linux to use python's webbrowser
    # This fixes issues where PyInstaller builds fail to launch the default browser
    if sys.platform == "linux":
        Logger.info("Patching QDesktopServices.openUrl for Linux")

        def open_url_linux(url):
            url_str = url.toString() if isinstance(url, QtCore.QUrl) else str(url)
            Logger.debug(f"Opening URL via subprocess xdg-open: {url_str}")
            import subprocess

            env = os.environ.copy()
            env.pop("LD_LIBRARY_PATH", None)
            try:
                subprocess.Popen(["xdg-open", url_str], env=env)
                return True
            except OSError:
                Logger.debug(f"Fallback to Opening URL via webbrowser: {url_str}")
                return webbrowser.open(url_str)

        QtGui.QDesktopServices.openUrl = open_url_linux

    # Fusion style + a palette from the theme tokens. Fusion + palette
    # covers the native widgets (dialogs, menus, combo popups) on every
    # platform; the MainWindow stylesheet does the rest. MainWindow then
    # applies the saved light/dark/system choice.
    theme.install(appl)

    form = MainWindow()
    form.show()
    appl.exec()


if __name__ == "__main__":
    run()
