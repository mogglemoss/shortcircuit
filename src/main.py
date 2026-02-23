import sys
import os
import traceback
from appdirs import AppDirs

# Fix for macOS Qt platform plugin crash
# This must be done before importing QApplication (which happens in shortcircuit.app)
import PySide6
plugin_path = os.path.join(os.path.dirname(PySide6.__file__), 'plugins', 'platforms')
if not os.path.exists(plugin_path):
    # Fallback for some pip installations (like yours)
    plugin_path = os.path.join(os.path.dirname(PySide6.__file__), 'Qt', 'plugins', 'platforms')
if os.path.exists(plugin_path):
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

from shortcircuit import app, __appslug__, __version__
from shortcircuit.model.logger import Logger


def excepthook(exc_type, exc_value, exc_tb):
  # Log the exception to file
  Logger.critical(
    "Uncaught exception",
    func="excepthook",
    exc_info=(exc_type, exc_value, exc_tb)
  )
  # Print to console/stderr for immediate feedback if running from terminal
  sys.stderr.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
  # Do not exit the application on uncaught exceptions, just log them.
  # sys.exit(1)


def main():
  sys.excepthook = excepthook
  
  # Initialize logger
  Logger()
  
  # Print log location to console for debugging
  app_dirs = AppDirs(__appslug__, "secondfry", version=__version__)
  log_file = os.path.join(app_dirs.user_log_dir, 'shortcircuit.log')
  print(f"Log file location: {log_file}")

  sys.exit(app.run())


if __name__ == "__main__":
  main()
