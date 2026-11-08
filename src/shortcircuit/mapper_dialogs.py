# mapper_dialogs.py
#
# Per-mapper configuration dialogs and the multi-mapper management dialog.
# Kept in upstream (secondfry/shortcircuit) style and structure so changes
# here stay easy to offer upstream; the fork's own UI lives in app.py.

from functools import partial
from typing import List, Optional

from PySide6 import QtCore, QtWidgets

from .model.mapper_config import (
  MapperConfig,
  TYPE_EVESCOUT,
  TYPE_PATHFINDER,
  TYPE_TRIPWIRE,
  TYPE_WANDERER,
)
from .view.gui_mappers import Ui_MappersDialog
from .view.gui_pathfinder import Ui_PathfinderDialog
from .view.gui_tripwire import Ui_TripwireDialog
from .view.gui_wanderer import Ui_WandererDialog


MAPPER_TYPE_LABELS = {
  TYPE_TRIPWIRE: "Tripwire",
  TYPE_EVESCOUT: "Eve Scout",
  TYPE_WANDERER: "Wanderer",
  TYPE_PATHFINDER: "Pathfinder",
}

MAPPER_TYPE_DESCRIPTIONS = {
  TYPE_TRIPWIRE: "Corp/alliance scanning map — needs an account on a Tripwire server",
  TYPE_EVESCOUT: "Public Thera and Turnur connections — no account needed",
  TYPE_WANDERER: "Wanderer map API — needs the map slug and an API token",
  TYPE_PATHFINDER: "Pathfinder instance exposing a JSON connections export",
}


class AddMapperTypeDialog(QtWidgets.QDialog):
  """
  Type picker for the Add flow: each mapper kind with a one-line
  description, instead of a bare dropdown prompt.
  """

  def __init__(self, parent=None):
    super().__init__(parent)
    self.setWindowTitle("Add mapper")
    self.setMinimumWidth(440)
    layout = QtWidgets.QVBoxLayout(self)
    layout.addWidget(QtWidgets.QLabel("What kind of mapper do you want to add?"))

    self.list_types = QtWidgets.QListWidget()
    self.list_types.setSpacing(2)
    for type_key, label in MAPPER_TYPE_LABELS.items():
      item = QtWidgets.QListWidgetItem()
      item.setData(QtCore.Qt.ItemDataRole.UserRole, type_key)
      item.setText("{}\n   {}".format(label, MAPPER_TYPE_DESCRIPTIONS.get(type_key, "")))
      self.list_types.addItem(item)
    self.list_types.setCurrentRow(0)
    self.list_types.itemDoubleClicked.connect(lambda _item: self.accept())
    layout.addWidget(self.list_types)

    buttons = QtWidgets.QDialogButtonBox(
      QtWidgets.QDialogButtonBox.StandardButton.Ok
      | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(self.accept)
    buttons.rejected.connect(self.reject)
    layout.addWidget(buttons)

  def selected_type(self):
    item = self.list_types.currentItem()
    if item is None:
      return None
    return item.data(QtCore.Qt.ItemDataRole.UserRole)


class TripwireDialog(QtWidgets.QDialog, Ui_TripwireDialog):
  """
  Per-instance Tripwire edit dialog, opened from MappersDialog.

  The dialog edits one Tripwire MapperConfig's name + credentials plus the
  global proxy value (proxy is persisted separately because a single
  requests session config applies to every Tripwire instance).
  """

  def __init__(
    self,
    name: str,
    trip_url: str,
    trip_user: str,
    trip_pass: str,
    proxy: str,
    parent=None,
  ):
    super().__init__(parent)
    self.setupUi(self)
    self.lineEdit_name.setText(name or "")
    self.lineEdit_url.setText(trip_url or "")
    self.lineEdit_user.setText(trip_user or "")
    self.lineEdit_pass.setText(trip_pass or "")
    self.lineEdit_proxy.setText(proxy or "")


class WandererDialog(QtWidgets.QDialog, Ui_WandererDialog):
  """
  Per-instance Wanderer edit dialog, opened from MappersDialog.

  Edits one Wanderer MapperConfig: name, instance URL, map slug and API
  bearer token (generated in Wanderer under Map Settings -> API).
  """

  def __init__(
    self,
    name: str,
    url: str,
    map_slug: str,
    token: str,
    parent=None,
  ):
    super().__init__(parent)
    self.setupUi(self)
    self.lineEdit_name.setText(name or "")
    self.lineEdit_url.setText(url or "")
    self.lineEdit_map.setText(map_slug or "")
    self.lineEdit_token.setText(token or "")


class PathfinderDialog(QtWidgets.QDialog, Ui_PathfinderDialog):
  """
  Per-instance Pathfinder edit dialog, opened from MappersDialog.

  Edits one Pathfinder MapperConfig: name, the JSON export URL and an
  optional bearer token.
  """

  def __init__(
    self,
    name: str,
    url: str,
    token: str,
    parent=None,
  ):
    super().__init__(parent)
    self.setupUi(self)
    self.lineEdit_name.setText(name or "")
    self.lineEdit_url.setText(url or "")
    self.lineEdit_token.setText(token or "")


class MappersDialog(QtWidgets.QDialog, Ui_MappersDialog):
  """
  Multi-mapper management dialog.

  Edits a working copy of the config list so Cancel actually discards
  changes. On OK, the caller reads self.configs and persists. Tripwire
  edits delegate to TripwireDialog; Eve Scout edits use a plain
  QInputDialog since only the name is user-editable (URL has a safe
  default).
  """

  COL_ENABLED = 0
  COL_NAME = 1
  COL_TYPE = 2
  COL_DETAILS = 3
  COL_URL = 4

  def __init__(
    self,
    configs: List[MapperConfig],
    proxy: str,
    parent=None,
  ):
    super().__init__(parent)
    self.setupUi(self)
    self.configs: List[MapperConfig] = [MapperConfig(**c.to_dict()) for c in configs]
    self.proxy = proxy or ""

    self.tableWidget_mappers.setColumnCount(5)
    self.tableWidget_mappers.setHorizontalHeaderLabels([
      "Enabled", "Name", "Type", "Details", "URL",
    ])
    header = self.tableWidget_mappers.horizontalHeader()
    header.setSectionResizeMode(self.COL_ENABLED, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(self.COL_NAME, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(self.COL_TYPE, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(self.COL_DETAILS, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(self.COL_URL, QtWidgets.QHeaderView.ResizeMode.Stretch)

    self.pushButton_add.clicked.connect(self._on_add)
    self.pushButton_edit.clicked.connect(self._on_edit)
    self.pushButton_remove.clicked.connect(self._on_remove)
    self.tableWidget_mappers.doubleClicked.connect(lambda _: self._on_edit())

    self._refresh_table()

  def _refresh_table(self):
    self.tableWidget_mappers.setRowCount(len(self.configs))
    for row, cfg in enumerate(self.configs):
      # Centered checkbox widget — a plain checkable QTableWidgetItem
      # pins the box to the left and leaves the rest of the cell empty,
      # which looks sloppy when the header text ("Enabled") is wider
      # than the box itself.
      container = QtWidgets.QWidget()
      layout = QtWidgets.QHBoxLayout(container)
      layout.setContentsMargins(0, 0, 0, 0)
      layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
      checkbox = QtWidgets.QCheckBox()
      checkbox.setChecked(cfg.enabled)
      checkbox.toggled.connect(partial(self._set_enabled, row))
      layout.addWidget(checkbox)
      self.tableWidget_mappers.setCellWidget(row, self.COL_ENABLED, container)

      name_item = QtWidgets.QTableWidgetItem(cfg.name)
      name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
      self.tableWidget_mappers.setItem(row, self.COL_NAME, name_item)

      type_item = QtWidgets.QTableWidgetItem(
        MAPPER_TYPE_LABELS.get(cfg.type, cfg.type)
      )
      type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
      self.tableWidget_mappers.setItem(row, self.COL_TYPE, type_item)

      details_item = QtWidgets.QTableWidgetItem(self._cfg_details(cfg))
      details_item.setFlags(details_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
      self.tableWidget_mappers.setItem(row, self.COL_DETAILS, details_item)

      url_item = QtWidgets.QTableWidgetItem(cfg.url)
      url_item.setFlags(url_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
      self.tableWidget_mappers.setItem(row, self.COL_URL, url_item)

  @staticmethod
  def _cfg_details(cfg: MapperConfig) -> str:
    """Human-readable per-type summary; never the secret itself."""
    if cfg.type == TYPE_WANDERER:
      return "map: {}".format(cfg.user) if cfg.user else "map not set"
    if cfg.type == TYPE_TRIPWIRE:
      return "user: {}".format(cfg.user) if cfg.user else "no account set"
    if cfg.type == TYPE_PATHFINDER:
      return "token set" if cfg.password else "no token"
    return ""

  def _set_enabled(self, row: int, checked: bool):
    if 0 <= row < len(self.configs):
      self.configs[row].enabled = checked

  @QtCore.Slot()
  def _on_add(self):
    picker = AddMapperTypeDialog(self)
    if not picker.exec():
      return
    type_key = picker.selected_type()
    if type_key is None:
      return

    if type_key == TYPE_TRIPWIRE:
      cfg = MapperConfig(
        type=TYPE_TRIPWIRE,
        name=self._unique_name("Tripwire"),
        enabled=True,
        url="https://tripwire.eve-apps.com",
      )
      edited = self._edit_tripwire(cfg)
    elif type_key == TYPE_WANDERER:
      cfg = MapperConfig(
        type=TYPE_WANDERER,
        name=self._unique_name("Wanderer"),
        enabled=True,
      )
      edited = self._edit_wanderer(cfg)
    elif type_key == TYPE_PATHFINDER:
      cfg = MapperConfig(
        type=TYPE_PATHFINDER,
        name=self._unique_name("Pathfinder"),
        enabled=True,
      )
      edited = self._edit_pathfinder(cfg)
    else:
      cfg = MapperConfig(
        type=TYPE_EVESCOUT,
        name=self._unique_name("Eve Scout"),
        enabled=True,
        url="https://api.eve-scout.com/v2/public/signatures",
      )
      edited = self._edit_evescout(cfg)

    if edited is not None:
      self.configs.append(edited)
      self._refresh_table()

  @QtCore.Slot()
  def _on_edit(self):
    row = self.tableWidget_mappers.currentRow()
    if row < 0 or row >= len(self.configs):
      return
    cfg = self.configs[row]
    if cfg.type == TYPE_TRIPWIRE:
      edited = self._edit_tripwire(cfg)
    elif cfg.type == TYPE_EVESCOUT:
      edited = self._edit_evescout(cfg)
    elif cfg.type == TYPE_WANDERER:
      edited = self._edit_wanderer(cfg)
    elif cfg.type == TYPE_PATHFINDER:
      edited = self._edit_pathfinder(cfg)
    else:
      edited = None
    if edited is not None:
      self.configs[row] = edited
      self._refresh_table()

  @QtCore.Slot()
  def _on_remove(self):
    row = self.tableWidget_mappers.currentRow()
    if row < 0 or row >= len(self.configs):
      return
    del self.configs[row]
    self._refresh_table()

  def _edit_tripwire(self, cfg: MapperConfig) -> Optional[MapperConfig]:
    dlg = TripwireDialog(
      name=cfg.name,
      trip_url=cfg.url,
      trip_user=cfg.user,
      trip_pass=cfg.password,
      proxy=self.proxy,
      parent=self,
    )
    if not dlg.exec():
      return None
    self.proxy = dlg.lineEdit_proxy.text()
    return MapperConfig(
      type=TYPE_TRIPWIRE,
      name=dlg.lineEdit_name.text().strip() or cfg.name,
      enabled=cfg.enabled,
      url=dlg.lineEdit_url.text().strip(),
      user=dlg.lineEdit_user.text(),
      password=dlg.lineEdit_pass.text(),
    )

  def _edit_wanderer(self, cfg: MapperConfig) -> Optional[MapperConfig]:
    dlg = WandererDialog(
      name=cfg.name,
      url=cfg.url,
      map_slug=cfg.user,
      token=cfg.password,
      parent=self,
    )
    if not dlg.exec():
      return None
    return MapperConfig(
      type=TYPE_WANDERER,
      name=dlg.lineEdit_name.text().strip() or cfg.name,
      enabled=cfg.enabled,
      url=dlg.lineEdit_url.text().strip(),
      user=dlg.lineEdit_map.text().strip(),
      password=dlg.lineEdit_token.text().strip(),
    )

  def _edit_pathfinder(self, cfg: MapperConfig) -> Optional[MapperConfig]:
    dlg = PathfinderDialog(
      name=cfg.name,
      url=cfg.url,
      token=cfg.password,
      parent=self,
    )
    if not dlg.exec():
      return None
    return MapperConfig(
      type=TYPE_PATHFINDER,
      name=dlg.lineEdit_name.text().strip() or cfg.name,
      enabled=cfg.enabled,
      url=dlg.lineEdit_url.text().strip(),
      password=dlg.lineEdit_token.text().strip(),
    )

  def _edit_evescout(self, cfg: MapperConfig) -> Optional[MapperConfig]:
    name, ok = QtWidgets.QInputDialog.getText(
      self,
      "Eve Scout",
      "Name:",
      QtWidgets.QLineEdit.EchoMode.Normal,
      cfg.name,
    )
    if not ok:
      return None
    return MapperConfig(
      type=TYPE_EVESCOUT,
      name=name.strip() or cfg.name,
      enabled=cfg.enabled,
      url=cfg.url or "https://api.eve-scout.com/v2/public/signatures",
    )

  def _unique_name(self, base: str) -> str:
    existing = {c.name for c in self.configs}
    if base not in existing:
      return base
    n = 2
    while f"{base} #{n}" in existing:
      n += 1
    return f"{base} #{n}"


