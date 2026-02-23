import sys
import os

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6 import QtWidgets, QtGui
from shortcircuit.app import MainWindow
import qdarktheme

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Apply theme to match main.py
    if hasattr(qdarktheme, 'setup_theme'):
        qdarktheme.setup_theme()
    elif hasattr(qdarktheme, 'load_stylesheet'):
        app.setStyleSheet(qdarktheme.load_stylesheet())

    window = MainWindow()
    
    # Mock route data covering all security classes
    mock_route = [
        {'id': 30000142, 'name': 'Jita', 'class': 'HS', 'security': 0.9, 'path_action': 'Start', 'path_info': ''},
        {'id': 30002813, 'name': 'Tama', 'class': 'LS', 'security': 0.3, 'path_action': 'Jump gate', 'path_info': ''},
        {'id': 30000000, 'name': 'Rancer', 'class': 'LS', 'security': 0.4, 'path_action': 'Jump gate', 'path_info': ''},
        {'id': 30000001, 'name': 'H-PA29', 'class': 'NS', 'security': -0.1, 'path_action': 'Jump gate', 'path_info': ''},
        {'id': 31000001, 'name': 'J123456', 'class': 'C3', 'security': -1.0, 'path_action': 'Jump wormhole', 'path_info': 'Large'},
        {'id': 31000005, 'name': 'Thera', 'class': 'WH', 'security': -1.0, 'path_action': 'Jump wormhole', 'path_info': 'XL'},
        {'id': 10000001, 'name': 'Triglav', 'class': '▲', 'security': -1.0, 'path_action': 'Jump gate', 'path_info': ''},
        {'id': 10001000, 'name': 'Zarzakh', 'class': 'Z', 'security': -1.0, 'path_action': 'Jump gate', 'path_info': ''},
    ]
    
    print("Populating table with mock data...")
    window.add_data_to_table(mock_route)
    
    window.label_status.setText("DEBUG: COLOR TEST")
    window.label_status.setStyleSheet("QLabel {color: #61afef; font-weight: bold;}")
    
    window.show()
    
    print("Window shown. Verify colors:")
    print("- HS: Green")
    print("- LS: Yellow")
    print("- NS: Red")
    print("- WH/C*: Blue")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

