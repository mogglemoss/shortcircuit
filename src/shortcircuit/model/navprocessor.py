# navprocessor.py
import os

from PySide6 import QtCore

from .logger import Logger
from .navigation import Navigation, evescout_augment


class NavProcessor(QtCore.QObject):
  """
  Navigation Processor (will work in a separate thread)
  """

  finished = QtCore.Signal(int, int)

  def __init__(self, nav: Navigation, parent=None):
    super().__init__(parent)
    self.evescout_enable = False
    self.nav = nav

  def process(self):
    if 'DEBUG' in os.environ:
      import debugpy
      debugpy.debug_this_thread()
    
    try:
      solar_map = self.nav.reset_chain()
      connections = self.nav.tripwire_augment(solar_map)
      evescout_connections = 0
      if self.evescout_enable:
        evescout_connections = evescout_augment(solar_map)
      if connections > 0 or evescout_connections > 0:
        self.nav.solar_map = solar_map
      self.finished.emit(connections, evescout_connections)
    except BaseException as e:
      Logger.error(f"NavProcessor exception: {e}", exc_info=True)
      # Emit -1 to signal error to the UI
      self.finished.emit(-1, -1)
