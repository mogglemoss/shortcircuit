# debug_qt.py
import sys
import os
import PySide6
from PySide6.QtWidgets import QApplication, QLabel

def main():
    print(f"PySide6 path: {os.path.dirname(PySide6.__file__)}")

    plugin_path = os.path.join(os.path.dirname(PySide6.__file__), 'plugins', 'platforms')
    print(f"Plugin path: {plugin_path}")
    print(f"Exists: {os.path.exists(plugin_path)}")

    # Force the plugin path
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

    # Enable debug output
    os.environ['QT_DEBUG_PLUGINS'] = '1'

    print("Initializing QApplication...")
    try:
        app = QApplication(sys.argv)
        print("QApplication initialized successfully.")
        label = QLabel("If you see this, Qt is working!")
        label.show()
        print("Window shown. Running event loop...")
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRASHED: {e}")

if __name__ == "__main__":
    main()