# pathfinder.py

from datetime import UTC, datetime
from typing import Any, Dict, Optional

import requests
from shortcircuit import USER_AGENT

from .evedb import EveDb, WormholeMassspan, WormholeSize, WormholeTimespan
from .logger import Logger
from .mapper_base import MapperSource
from .solarmap import ConnectionType, SolarMap


class Pathfinder(MapperSource):
  """
  Pathfinder wormhole mapper connections provider.

  Pathfinder instances don't expose a standard public connections API, so
  this source targets a JSON export endpoint: either a URL ending in
  .json, an explicit /api path, or a base URL to which /api/connections
  is appended. Each entry needs `source` and `target` system ids;
  signature, type, life, mass, size and updated_at fields are read when
  present.
  """
  TIMEOUT = 10

  def __init__(
    self,
    url: str,
    token: str = '',
    name: str = "Pathfinder",
  ):
    url = (url or '').strip().rstrip('/')
    if url and not (url.startswith('http://') or url.startswith('https://')):
      url = 'https://' + url
    self.url = url
    self.token = (token or '').strip()
    self.name = name
    self.eve_db = EveDb()

  def augment_map(self, solar_map: SolarMap):
    """
    :param solar_map: SolarMap
    :return: Number of connections in case of success, -1 in case of failure
    """
    connections_list = self._fetch_connections()
    if connections_list is None:
      return -1

    connections = 0
    for conn in connections_list:
      if self._process_connection(conn, solar_map):
        connections += 1
    return connections

  def _fetch_connections(self) -> Optional[list]:
    is_valid, error = self.validate_config()
    if not is_valid:
      Logger.error(f"Pathfinder '{self.name}' misconfigured: {error}")
      return None

    target_url = self.url
    if not target_url.endswith('.json') and '/api' not in target_url:
      target_url = f"{target_url}/api/connections"

    headers = {
      'User-Agent': USER_AGENT,
      'Accept': 'application/json',
    }
    if self.token:
      headers['Authorization'] = f"Bearer {self.token}"

    try:
      result = requests.get(
        url=target_url,
        headers=headers,
        timeout=Pathfinder.TIMEOUT,
      )
    except requests.exceptions.RequestException as e:
      Logger.error(f"Exception raised while trying to get Pathfinder data from '{target_url}'")
      Logger.error(e)
      return None

    if result.status_code != 200:
      Logger.error(f"Pathfinder '{self.name}': HTTP {result.status_code}")
      return None

    try:
      payload = result.json()
    except ValueError as e:
      Logger.error(f"Pathfinder '{self.name}': invalid JSON response: {e}")
      return None

    connections_list = (
      payload.get('connections', []) if isinstance(payload, dict) else payload
    )
    if not isinstance(connections_list, list):
      Logger.error(f"Pathfinder '{self.name}': unexpected response shape")
      return None
    return connections_list

  def _process_connection(self, conn: Dict[str, Any], solar_map: SolarMap) -> bool:
    try:
      source = int(conn.get('source', 0))
      dest = int(conn.get('target', 0))
    except (TypeError, ValueError):
      return False
    if not source or not dest:
      return False

    sig_source = conn.get('source_sig') or '???'
    sig_dest = conn.get('target_sig') or '???'
    code_source = conn.get('type') or 'K162'

    life_str = str(conn.get('life', 'stable')).lower()
    wh_life = (
      WormholeTimespan.CRITICAL if 'crit' in life_str else WormholeTimespan.STABLE
    )

    mass_str = str(conn.get('mass', 'stable')).lower()
    if 'destab' in mass_str:
      wh_mass = WormholeMassspan.DESTAB
    elif 'crit' in mass_str:
      wh_mass = WormholeMassspan.CRITICAL
    else:
      wh_mass = WormholeMassspan.STABLE

    wh_size = self.eve_db.get_whsize_by_code(code_source)
    if not WormholeSize.valid(wh_size):
      size_str = str(conn.get('size', '')).lower()
      if 'xl' in size_str:
        wh_size = WormholeSize.XLARGE
      elif 'large' in size_str:
        wh_size = WormholeSize.LARGE
      elif 'medium' in size_str:
        wh_size = WormholeSize.MEDIUM
      elif 'small' in size_str:
        wh_size = WormholeSize.SMALL
      else:
        wh_size = self.eve_db.get_whsize_by_system(source, dest)

    solar_map.add_connection(
      source,
      dest,
      ConnectionType.WORMHOLE,
      [
        sig_source,
        code_source,
        sig_dest,
        'K162',
        wh_size,
        wh_life,
        wh_mass,
        self._time_elapsed(conn.get('updated_at')),
      ],
      source_name=self.name,
    )
    return True

  @staticmethod
  def _time_elapsed(updated_at: Optional[str]) -> float:
    """Hours since the connection was last updated; 0.0 when unknown."""
    if not updated_at:
      return 0.0
    try:
      if 'Z' in updated_at:
        updated_at = updated_at.replace('Z', '+00:00')
      last_modified = datetime.fromisoformat(updated_at)
      if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=UTC)
    except ValueError:
      return 0.0
    delta = datetime.now(UTC) - last_modified
    return round(delta.total_seconds() / 3600.0, 1)

  def get_name(self) -> str:
    """
    Get the name of this Pathfinder instance.

    Returns:
      The name of this mapper source
    """
    return self.name

  def validate_config(self) -> tuple[bool, Optional[str]]:
    """
    Validate the Pathfinder configuration.

    Returns:
      Tuple of (is_valid, error_message)
    """
    if not self.url:
      return False, "URL is required"
    return True, None
