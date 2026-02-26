# navprocessor.py
import os

from PySide6 import QtCore

from .logger import Logger
from .navigation import Navigation


class NavProcessor(QtCore.QObject):
  """
  Navigation Processor (will work in a separate thread)
  """

  finished = QtCore.Signal(dict)

  def __init__(self, nav: Navigation, parent=None):
    super().__init__(parent)
    self.nav = nav
    self.source_id = None

  def process(self):
    if 'DEBUG' in os.environ:
      import debugpy
      debugpy.debug_this_thread()
    
    try:
      if self.source_id:
        # Partial refresh: use existing map
        solar_map = self.nav.solar_map
        results = self.nav.augment_source(solar_map, self.source_id)
      else:
        # Full refresh: reset chain
        solar_map = self.nav.reset_chain()
        results = self.nav.augment_map(solar_map)
      
      # Check if we have any connections from any source
      total_connections = sum(count for count in results.values() if count > 0)
      
      if total_connections > 0:
        self.nav.solar_map = solar_map
      self.finished.emit(results)
    except BaseException as e:
      Logger.error(f"NavProcessor exception: {e}", exc_info=True)
      self.finished.emit({})
    finally:
      self.source_id = None
