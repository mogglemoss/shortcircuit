# src/shortcircuit/model/mapper_registry.py

from typing import Dict, List, Protocol
from .solarmap import SolarMap
from .logger import Logger

class MapperSource(Protocol):
  def augment_map(self, solar_map: SolarMap) -> int:
    ...

  def get_name(self) -> str:
    ...

class MapperRegistry:
  def __init__(self):
    self.sources: List[MapperSource] = []

  def register(self, source: MapperSource):
    self.sources.append(source)

  def clear(self):
    self.sources.clear()

  def augment_map(self, solar_map: SolarMap) -> Dict[str, int]:
    results = {}
    for source in self.sources:
      try:
        count = source.augment_map(solar_map)
        results[source.get_name()] = count
      except Exception as e:
        Logger.error(f"Error in mapper {source.get_name()}: {e}")
        results[source.get_name()] = -1
    return results

