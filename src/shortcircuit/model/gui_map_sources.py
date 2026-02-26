from PySide6 import QtWidgets, QtCore, QtGui
from shortcircuit.model.source_manager import SourceManager
from shortcircuit.model.mapsource import SourceType
from shortcircuit.model.tripwire_source import TripwireSource
from shortcircuit.model.wanderer_source import WandererSource
from shortcircuit.model.pathfinder_source import PathfinderSource
from shortcircuit.model.evescout_source import EveScoutSource

class BaseSourceConfigWidget(QtWidgets.QWidget):
    """Base widget for source-specific configuration forms."""
    changed = QtCore.Signal()

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self.layout = QtWidgets.QFormLayout(self)
        
        self.name_edit = QtWidgets.QLineEdit(self.source.name)
        self.name_edit.textChanged.connect(self.on_name_changed)
        
        self.enabled_check = QtWidgets.QCheckBox("Enabled")
        self.enabled_check.setChecked(self.source.enabled)
        self.enabled_check.toggled.connect(self.on_enabled_toggled)
        
        self.layout.addRow("Display Name:", self.name_edit)
        self.layout.addRow(self.enabled_check)

        self.test_btn = QtWidgets.QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.on_test_connection)
        self.layout.addRow(self.test_btn)

    def on_name_changed(self, text):
        self.source.name = text
        self.changed.emit()

    def on_enabled_toggled(self, checked):
        self.source.enabled = checked
        self.changed.emit()

    def on_test_connection(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            success, message = self.source.connect()
            if success:
                QtWidgets.QMessageBox.information(self, "Connection Test", f"Connection successful!\n\n{message}")
            else:
                QtWidgets.QMessageBox.warning(self, "Connection Test", f"Connection failed. Please check your settings.\n\nError: {message}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Connection Test", f"An error occurred: {str(e)}")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()


class TripwireConfigWidget(BaseSourceConfigWidget):
    def __init__(self, source: TripwireSource, parent=None):
        super().__init__(source, parent)
        self.url_edit = QtWidgets.QLineEdit(source.url)
        self.user_edit = QtWidgets.QLineEdit(source.username)
        self.pass_edit = QtWidgets.QLineEdit(source.password)
        self.pass_edit.setEchoMode(QtWidgets.QLineEdit.Password)

        self.url_edit.textChanged.connect(self.update_config)
        self.user_edit.textChanged.connect(self.update_config)
        self.pass_edit.textChanged.connect(self.update_config)

        self.layout.addRow("URL:", self.url_edit)
        self.layout.addRow("Username:", self.user_edit)
        self.layout.addRow("Password:", self.pass_edit)

    def update_config(self):
        self.source.url = self.url_edit.text()
        self.source.username = self.user_edit.text()
        self.source.password = self.pass_edit.text()
        # Update underlying Tripwire instance
        self.source._tripwire.url = self.source.url
        self.source._tripwire.username = self.source.username
        self.source._tripwire.password = self.source.password
        self.changed.emit()


class WandererConfigWidget(BaseSourceConfigWidget):
    def __init__(self, source: WandererSource, parent=None):
        super().__init__(source, parent)
        self.url_edit = QtWidgets.QLineEdit(source.url)
        self.map_edit = QtWidgets.QLineEdit(source.map_id)
        self.token_edit = QtWidgets.QLineEdit(source.token)

        self.url_edit.textChanged.connect(self.update_config)
        self.map_edit.textChanged.connect(self.update_config)
        self.token_edit.textChanged.connect(self.update_config)

        self.layout.addRow("URL:", self.url_edit)
        self.layout.addRow("Map ID:", self.map_edit)
        self.layout.addRow("API Token:", self.token_edit)

    def update_config(self):
        self.source.url = self.url_edit.text()
        self.source.map_id = self.map_edit.text()
        self.source.token = self.token_edit.text()
        # Update underlying Wanderer instance
        self.source._wanderer.url = self.source.url
        self.source._wanderer.map_id = self.source.map_id
        self.source._wanderer.token = self.source.token
        self.changed.emit()


class PathfinderConfigWidget(BaseSourceConfigWidget):
    def __init__(self, source: PathfinderSource, parent=None):
        super().__init__(source, parent)
        self.url_edit = QtWidgets.QLineEdit(source.url)
        self.token_edit = QtWidgets.QLineEdit(source.token)

        self.url_edit.textChanged.connect(self.update_config)
        self.token_edit.textChanged.connect(self.update_config)

        self.layout.addRow("URL:", self.url_edit)
        self.layout.addRow("API Token:", self.token_edit)

    def update_config(self):
        self.source.url = self.url_edit.text()
        self.source.token = self.token_edit.text()
        # Update underlying Pathfinder instance
        self.source._pathfinder.url = self.source.url
        self.source._pathfinder.token = self.source.token
        self.changed.emit()


class MapSourcesPage(QtWidgets.QWidget):
    """The main settings page for managing multiple map sources."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sm = SourceManager()
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)

        # Left Pane: List and Add/Remove buttons
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        
        self.source_list = QtWidgets.QListWidget()
        self.source_list.currentRowChanged.connect(self.on_source_selected)
        
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add Source")
        self.add_btn.clicked.connect(self.on_add_clicked)
        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.remove_btn.clicked.connect(self.on_remove_clicked)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        
        left_layout.addWidget(self.source_list)
        left_layout.addLayout(btn_layout)

        # Right Pane: Configuration Stack
        self.config_stack = QtWidgets.QStackedWidget()
        self.empty_label = QtWidgets.QLabel("Select a source to configure or add a new one.")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.config_stack.addWidget(self.empty_label)

        layout.addWidget(left_widget, 1)
        layout.addWidget(self.config_stack, 2)

    def refresh_list(self):
        self.source_list.clear()
        for source in self.sm.get_sources():
            item = QtWidgets.QListWidgetItem(f"{source.name} ({source.type.value})")
            item.setData(QtCore.Qt.UserRole, source.id)
            self.source_list.addItem(item)

    def on_source_selected(self, index):
        if index < 0:
            self.config_stack.setCurrentIndex(0)
            return

        source_id = self.source_list.item(index).data(QtCore.Qt.UserRole)
        source = next((s for s in self.sm.get_sources() if s.id == source_id), None)
        
        if source:
            widget = self.create_config_widget(source)
            # Clear previous widgets in stack except the empty label
            while self.config_stack.count() > 1:
                widget_to_remove = self.config_stack.widget(1)
                self.config_stack.removeWidget(widget_to_remove)
                widget_to_remove.deleteLater()
            
            self.config_stack.addWidget(widget)
            self.config_stack.setCurrentWidget(widget)

    def create_config_widget(self, source):
        widget_map = {
            SourceType.TRIPWIRE: TripwireConfigWidget,
            SourceType.WANDERER: WandererConfigWidget,
            SourceType.PATHFINDER: PathfinderConfigWidget,
            SourceType.EVESCOUT: BaseSourceConfigWidget, # EveScout only has base fields
        }
        widget_cls = widget_map.get(source.type, BaseSourceConfigWidget)
        widget = widget_cls(source)
        widget.changed.connect(self.on_config_changed)
        return widget

    def on_config_changed(self):
        # Update the list item text in case the name changed
        current_row = self.source_list.currentRow()
        if current_row >= 0:
            source_id = self.source_list.item(current_row).data(QtCore.Qt.UserRole)
            source = next((s for s in self.sm.get_sources() if s.id == source_id), None)
            if source:
                self.source_list.item(current_row).setText(f"{source.name} ({source.type.value})")
        
        self.sm.save_configuration()

    def on_add_clicked(self):
        menu = QtWidgets.QMenu(self)
        for st in SourceType:
            action = menu.addAction(st.value.capitalize())
            action.setData(st)
            action.triggered.connect(lambda checked=False, t=st: self.add_source(t))
        menu.exec(QtGui.QCursor.pos())

    def add_source(self, source_type):
        source_cls = self.sm._registry.get(source_type)
        if source_cls:
            new_source = source_cls(name=f"New {source_type.value.capitalize()}")
            self.sm.add_source(new_source)
            self.refresh_list()
            self.source_list.setCurrentRow(self.source_list.count() - 1)

    def on_remove_clicked(self):
        current_row = self.source_list.currentRow()
        if current_row >= 0:
            source_id = self.source_list.item(current_row).data(QtCore.Qt.UserRole)
            self.sm.remove_source(source_id)
            self.refresh_list()