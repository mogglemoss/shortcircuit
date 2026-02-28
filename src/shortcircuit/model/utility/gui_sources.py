from PySide6 import QtCore, QtGui, QtWidgets
import copy
from shortcircuit.model.mapsource import SourceType
from shortcircuit.model.tripwire_source import TripwireSource
from shortcircuit.model.wanderer_source import WandererSource
from shortcircuit.model.pathfinder_source import PathfinderSource
from shortcircuit.model.evescout_source import EveScoutSource
import uuid


class SourceConfigurationDialog(QtWidgets.QDialog):
    sources_saved = QtCore.Signal()

    def __init__(self, source_manager, parent=None):
        super().__init__(parent)
        self.source_manager = source_manager
        self.setWindowTitle("Wormhole Sources Configuration")
        self.setMinimumSize(700, 450)

        # Working copy of sources
        self.sources = []
        for src in self.source_manager.get_sources():
            cls = self.source_manager._registry.get(src.type)
            if cls:
                self.sources.append(cls.from_json(src.to_json()))

        main_layout = QtWidgets.QVBoxLayout(self)

        # Splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: List of sources
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.source_list = QtWidgets.QListWidget()
        self.source_list.currentRowChanged.connect(self._on_source_selected)
        left_layout.addWidget(self.source_list)

        # Buttons to add/remove sources
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("+ Add Source")
        self.btn_add.clicked.connect(self._on_add_source)
        self.btn_remove = QtWidgets.QPushButton("- Remove")
        self.btn_remove.clicked.connect(self._on_remove_source)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_widget)

        # Right panel: Configuration form
        self.detail_widget = QtWidgets.QStackedWidget()
        splitter.addWidget(self.detail_widget)

        # Empty page
        self.empty_page = QtWidgets.QWidget()
        empty_layout = QtWidgets.QVBoxLayout(self.empty_page)
        empty_layout.addWidget(
            QtWidgets.QLabel("Select a source or add a new one."), alignment=QtCore.Qt.AlignCenter
        )
        self.detail_widget.addWidget(self.empty_page)

        # Generic Form Page
        self.form_page = QtWidgets.QWidget()
        self.form_layout = QtWidgets.QFormLayout(self.form_page)
        self.detail_widget.addWidget(self.form_page)

        splitter.setSizes([200, 500])

        # Bottom buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_save.setFixedWidth(100)
        self.btn_save.clicked.connect(self._save_only)
        btn_layout.addWidget(self.btn_save)

        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_close.setFixedWidth(100)
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        main_layout.addLayout(btn_layout)

        # Populate list
        self._populate_list()

    def _populate_list(self):
        self.source_list.clear()
        for src in self.sources:
            item = QtWidgets.QListWidgetItem(f"[{src.type.value.capitalize()}] {src.name}")
            item.setCheckState(QtCore.Qt.Checked if src.enabled else QtCore.Qt.Unchecked)
            self.source_list.addItem(item)
        if self.sources:
            self.source_list.setCurrentRow(0)
        else:
            self.detail_widget.setCurrentWidget(self.empty_page)

    def _on_source_selected(self, row):
        if row < 0 or row >= len(self.sources):
            self.detail_widget.setCurrentWidget(self.empty_page)
            return

        # Always save current form state back to model before switching
        # (Assuming they switch row after editing, we need real-time data binding.
        # Simplest is to bind text changes directly)

        src = self.sources[row]
        self._build_form(src)
        self.detail_widget.setCurrentWidget(self.form_page)

    def _on_test_connection(self, src):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            success, message = src.connect()
            if success:
                QtWidgets.QMessageBox.information(
                    self, "Connection Test", f"Connection successful!\n\n{message}"
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Connection Test",
                    f"Connection failed. Please check your settings.\n\nError: {message}",
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Connection Test", f"An error occurred: {str(e)}")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _build_form(self, src):
        # Clear existing form
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)

        self.test_btn = QtWidgets.QPushButton("Test Connection")
        self.test_btn.clicked.connect(lambda: self._on_test_connection(src))
        self.form_layout.addRow(self.test_btn)

        # Common fields
        self.edit_name = QtWidgets.QLineEdit(src.name)
        self.edit_name.textChanged.connect(lambda t: self._update_model_field(src, "name", t))
        self.form_layout.addRow("Name:", self.edit_name)

        if src.type == SourceType.TRIPWIRE:
            self.edit_url = QtWidgets.QLineEdit(src.url)
            self.edit_url.textChanged.connect(lambda t: self._update_model_field(src, "url", t))
            self.form_layout.addRow("URL:", self.edit_url)

            self.edit_user = QtWidgets.QLineEdit(src.username)
            self.edit_user.textChanged.connect(
                lambda t: self._update_model_field(src, "username", t)
            )
            self.form_layout.addRow("Username:", self.edit_user)

            self.edit_pass = QtWidgets.QLineEdit(src.password)
            self.edit_pass.setEchoMode(QtWidgets.QLineEdit.Password)
            self.edit_pass.textChanged.connect(
                lambda t: self._update_model_field(src, "password", t)
            )
            self.form_layout.addRow("Password:", self.edit_pass)

        elif src.type == SourceType.WANDERER:
            self.edit_url = QtWidgets.QLineEdit(src.url)
            self.edit_url.textChanged.connect(lambda t: self._update_model_field(src, "url", t))
            self.form_layout.addRow("URL:", self.edit_url)

            self.edit_map = QtWidgets.QLineEdit(src.map_id)
            self.edit_map.textChanged.connect(lambda t: self._update_model_field(src, "map_id", t))
            self.form_layout.addRow("Map ID:", self.edit_map)

            self.edit_token = QtWidgets.QLineEdit(src.token)
            self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
            self.edit_token.textChanged.connect(lambda t: self._update_model_field(src, "token", t))
            self.form_layout.addRow("Token:", self.edit_token)

        elif src.type == SourceType.PATHFINDER:
            self.edit_url = QtWidgets.QLineEdit(src.url)
            self.edit_url.textChanged.connect(lambda t: self._update_model_field(src, "url", t))
            self.form_layout.addRow("URL:", self.edit_url)

            self.edit_token = QtWidgets.QLineEdit(src.token)
            self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
            self.edit_token.textChanged.connect(lambda t: self._update_model_field(src, "token", t))
            self.form_layout.addRow("API Token:", self.edit_token)

            lbl_pf_help = QtWidgets.QLabel("Look in: Profile > Settings > API Access")
            lbl_pf_help.setStyleSheet("color: #abb2bf; font-style: italic; font-size: 11px;")
            self.form_layout.addRow("", lbl_pf_help)

        elif src.type == SourceType.EVESCOUT:
            lbl_es_help = QtWidgets.QLabel("Eve-Scout provides public Thera connections.")
            self.form_layout.addRow("", lbl_es_help)

    def _update_model_field(self, src, field, value):
        setattr(src, field, value)
        # Update list item if name changed
        if field == "name":
            row = self.source_list.currentRow()
            if row >= 0:
                item = self.source_list.item(row)
                item.setText(f"[{src.type.value.capitalize()}] {value}")

    def _on_add_source(self):
        types = [t.value.capitalize() for t in SourceType]
        type_str, ok = QtWidgets.QInputDialog.getItem(
            self, "Add Source", "Select Source Type:", types, 0, False
        )
        if ok and type_str:
            stype = SourceType(type_str.lower())

            # Prevent multiple EveScout sources
            if stype == SourceType.EVESCOUT and any(
                s.type == SourceType.EVESCOUT for s in self.sources
            ):
                QtWidgets.QMessageBox.warning(self, "Warning", "Eve-Scout source already exists.")
                return

            cls = self.source_manager._registry.get(stype)
            if cls:
                new_src = cls(name=f"New {type_str}", id=str(uuid.uuid4()))
                self.sources.append(new_src)
                self._populate_list()
                self.source_list.setCurrentRow(len(self.sources) - 1)

    def _on_remove_source(self):
        row = self.source_list.currentRow()
        if row >= 0:
            del self.sources[row]
            self._populate_list()

    def _save_only(self):
        # Apply checkbox states
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            self.sources[i].enabled = item.checkState() == QtCore.Qt.Checked

        self.source_manager.sources = self.sources
        self.source_manager.save_configuration()
        self.sources_saved.emit()

    def accept(self):
        super().accept()
