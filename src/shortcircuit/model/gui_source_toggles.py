from PySide6 import QtWidgets, QtCore, QtGui
from datetime import datetime
from shortcircuit.model.source_manager import SourceManager

class SourceStatusWidget(QtWidgets.QPushButton):
    """
    A status bar widget that allows quick toggling of map sources.
    """
    manage_requested = QtCore.Signal()
    refresh_requested = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__("Map Sources", parent)
        self.sm = SourceManager()
        self.setFlat(True)
        
        # Create the menu
        self.menu = QtWidgets.QMenu(self)
        self.setMenu(self.menu)
        
        # Update menu whenever sources change (added/removed/toggled)
        self.sm.sources_changed.connect(self.refresh_menu)
        self.refresh_menu()

    def refresh_menu(self):
        self.menu.clear()
        sources = self.sm.get_sources()
        
        now = datetime.now()

        if not sources:
            action = self.menu.addAction("No sources configured")
            action.setEnabled(False)
            return

        for source in sources:
            # Create a sub-menu for each source
            title = f"{source.name} ({source.type.value})"
            if source.last_updated:
                delta = now - source.last_updated
                secs = int(delta.total_seconds())
                if secs < 60:
                    time_str = "just now"
                elif secs < 3600:
                    time_str = f"{secs // 60}m ago"
                else:
                    time_str = f"{secs // 3600}h {(secs % 3600) // 60}m ago"
                title += f" [{time_str}]"

            source_menu = QtWidgets.QMenu(title, self.menu)
            self.menu.addMenu(source_menu)
            
            # Enable/Disable action
            toggle_action = QtGui.QAction("Enabled", source_menu)
            toggle_action.setCheckable(True)
            toggle_action.setChecked(source.enabled)
            toggle_action.triggered.connect(lambda checked, s=source: self.toggle_source(s, checked))
            source_menu.addAction(toggle_action)
            
            # Refresh action
            refresh_action = QtGui.QAction("Refresh Now", source_menu)
            refresh_action.setEnabled(source.enabled)
            refresh_action.triggered.connect(lambda _, s=source: self.refresh_requested.emit(s.id))
            source_menu.addAction(refresh_action)
            
        self.menu.addSeparator()
        manage_action = self.menu.addAction("Manage Sources...")
        manage_action.triggered.connect(self.manage_requested.emit)

    def toggle_source(self, source, enabled):
        source.enabled = enabled
        # Saving configuration triggers the sources_changed signal, 
        # which will refresh this menu and notify other components.
        self.sm.save_configuration()