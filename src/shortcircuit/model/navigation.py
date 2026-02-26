# navigation.py

from typing import TYPE_CHECKING, List

from .evedb import EveDb, SystemDescription, WormholeMassspan, WormholeSize, WormholeTimespan
from .solarmap import ConnectionType, SolarMap

if TYPE_CHECKING:
  from shortcircuit.app import MainWindow


class Navigation:
  """
  Navigation
  """

  def __init__(self, app_obj: 'MainWindow', eve_db: EveDb):
    self.app_obj = app_obj
    self.eve_db = eve_db

    self.solar_map = SolarMap(self.eve_db)
    
    # Keep a reference to the Tripwire instance for cookie management
    self.tripwire_instance = None

  def reset_chain(self):
    self.solar_map = SolarMap(self.eve_db)
    return self.solar_map

  def setup_mappers(self):
    """Configures the map sources based on current app settings."""
    from shortcircuit.model.source_manager import SourceManager
    from shortcircuit.model.mapsource import SourceType
    from shortcircuit.model.tripwire_source import TripwireSource
    from shortcircuit.model.pathfinder_source import PathfinderSource
    from shortcircuit.model.evescout_source import EveScoutSource
    from shortcircuit.model.wanderer_source import WandererSource

    sm = SourceManager()

    # Register source classes if not already registered
    if not sm._registry:
      sm.register_source_class(SourceType.TRIPWIRE, TripwireSource)
      sm.register_source_class(SourceType.PATHFINDER, PathfinderSource)
      sm.register_source_class(SourceType.EVESCOUT, EveScoutSource)
      sm.register_source_class(SourceType.WANDERER, WandererSource)

    sm.load_configuration()

    self.tripwire_instance = None
    for source in sm.get_enabled_sources():
      if source.type == SourceType.TRIPWIRE:
        self.tripwire_instance = source._tripwire
        break

  def augment_map(self, solar_map: SolarMap):
    from shortcircuit.model.source_manager import SourceManager
    sm = SourceManager()
    return sm.fetch_all(solar_map)

  def augment_source(self, solar_map: SolarMap, source_id: str):
    from shortcircuit.model.source_manager import SourceManager
    sm = SourceManager()
    return sm.fetch_one(source_id, solar_map)

  # FIXME refactor neighbor info - weights
  @staticmethod
  def _get_instructions(weight):
    if not weight:
      return "Destination reached"

    if weight[0] == ConnectionType.GATE:
      return "Jump gate"

    if weight[0] == ConnectionType.WORMHOLE:
      data = weight[1]
      wh_sig = data[0]
      wh_code = data[1]
      instruction = "Jump wormhole\n{} [{}]".format(wh_sig, wh_code)
      
      if len(data) > 6:
        source = data[6]
        if source:
          instruction += " [{}]".format(source)
      return instruction

    return "Instructions unclear, initiate self-destruct"

  # FIXME refactor neighbor info - weights
  @staticmethod
  def _get_additional_info(weight, weight_back):
    if not weight or not weight_back:
      return

    if weight_back[0] != ConnectionType.WORMHOLE:
      return

    data = weight_back[1]
    wh_sig = data[0]
    wh_code = data[1]
    wh_size = data[2]
    wh_life = data[3]
    wh_mass = data[4]
    time_elapsed = data[5]
    source_name = data[6] if len(data) > 6 else None

    # Wormhole size
    wh_size_text = "Unknown"
    if wh_size == WormholeSize.SMALL:
      wh_size_text = "Small"
    if wh_size == WormholeSize.MEDIUM:
      wh_size_text = "Medium"
    if wh_size == WormholeSize.LARGE:
      wh_size_text = "Large"
    elif wh_size == WormholeSize.XLARGE:
      wh_size_text = "X-large"

    # Wormhole life
    wh_life_text = "Timespan unknown"
    if wh_life == WormholeTimespan.STABLE:
      wh_life_text = "Stable"
    if wh_life == WormholeTimespan.CRITICAL:
      wh_life_text = "Critical"

    # Wormhole mass
    wh_mass_text = "Massspan unknown"
    if wh_mass == WormholeMassspan.STABLE:
      wh_mass_text = "Stable"
    if wh_mass == WormholeMassspan.DESTAB:
      wh_mass_text = "Destab"
    if wh_mass == WormholeMassspan.CRITICAL:
      wh_mass_text = "Critical"

    # Return signature
    info_text = "Return sig: {0} [{1}], Updated: {5}h ago\nSize: {2}, Life: {3}, Mass: {4}".format(
      wh_sig, wh_code, wh_size_text, wh_life_text, wh_mass_text, time_elapsed
    )

    if source_name:
      info_text += "\nSource: {}".format(source_name)
    return info_text

  def route(self, source: int, destination: int):
    path = self.solar_map.shortest_path(
      source,
      destination,
      self.app_obj.get_restrictions(),
    )

    # Construct route
    route: List[SystemDescription] = []
    for idx, x in enumerate(path):
      if idx == len(path) - 1:
        weight = None
        weight_back = None
      else:
        source = self.solar_map.get_system(x)
        dest = self.solar_map.get_system(path[idx + 1])
        weight = source.get_weight(dest)
        weight_back = dest.get_weight(source)

      route_step = self.eve_db.system_desc[x]
      route_step['path_action'] = Navigation._get_instructions(weight)
      route_step['path_info'] = Navigation._get_additional_info(
        weight,
        weight_back,
      )
      route_step['path_data'] = weight
      route.append(route_step)

    if not route:
      return (route, 'Path is not found')

    # Construct short format
    short_format = list()
    flag_gate = 0
    for rsid, route_step in enumerate(route):
      # We are adding systems in backwards manner, so skip first one
      if rsid == 0:
        continue

      prev_route_step = route[rsid - 1]

      # We jumped to this system via wormhole
      if prev_route_step['path_data'][0] == ConnectionType.WORMHOLE:
        # ...in case of multiple previous gate jumps, indicate that
        if flag_gate > 1:
          short_format.extend(['...', '-->'])

        # Add previous system to route
        short_format.extend([
          '{} [{}]'.format(
            prev_route_step['name'],
            # FIXME my eyes are bleeding, this gets signature from weight param
            prev_route_step['path_data'][1][0],
          ),
          '~~>'
        ])
        flag_gate = 0
        continue

      # We are skipping multiple gate jumps
      if flag_gate:
        flag_gate += 1
        continue

      # Add previous system to route
      short_format.extend([prev_route_step['name'], '-->'])
      flag_gate += 1

    # Add last system
    # ...in case of multiple previous gate jumps, indicate that
    if flag_gate > 1:
      short_format.extend(['...', '-->'])
    short_format.append(route[-1]['name'])

    short_format = 'Short Circuit: `{}`'.format(' '.join(short_format))

    return (route, short_format)
