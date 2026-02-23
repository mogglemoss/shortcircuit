# src/shortcircuit/model/pathfinder.py

import asyncio
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List, Optional

from shortcircuit import USER_AGENT
from .evedb import EveDb, WormholeSize, WormholeTimespan, WormholeMassspan
from .solarmap import SolarMap, ConnectionType
from .logger import Logger


class Pathfinder:
  """
  Pathfinder handler
  """

  def __init__(self, url: str, token: str, name: str = "Pathfinder"):
    self.eve_db = EveDb()
    self.url = url.strip().rstrip('/')
    self.token = token
    self.name = name

  def get_name(self) -> str:
    return self.name

  def test_credentials(self) -> Tuple[bool, str]:
    return asyncio.run(self._test_credentials_task())

  async def _test_credentials_task(self) -> Tuple[bool, str]:
    import httpx

    try:
      async with httpx.AsyncClient(verify=True) as client:
        # Check if we can reach the server
        response = await client.get(
          self.url,
          headers={'User-Agent': USER_AGENT},
          follow_redirects=True,
          timeout=10.0
        )
        
        if response.status_code < 400:
          return True, "Connection successful (URL reachable)"
        else:
          return False, f"HTTP Error {response.status_code}"
    except Exception as e:
      return False, f"Connection failed: {e}"

  async def _augment_map_async(self, solar_map: SolarMap) -> int:
    import httpx

    # Construct the API endpoint. 
    # If the user provided a base URL (e.g. https://pathfinder.example.com),
    # we assume the API is at /api/connections or similar.
    # Adjust this endpoint based on your specific Pathfinder export configuration.
    target_url = self.url
    if not target_url.endswith('.json') and '/api' not in target_url:
        target_url = f"{target_url}/api/connections"

    headers = {
      'User-Agent': USER_AGENT,
      'Authorization': f'Bearer {self.token}' if self.token else None,
      'Accept': 'application/json'
    }
    # Remove None headers
    headers = {k: v for k, v in headers.items() if v is not None}

    try:
      async with httpx.AsyncClient(verify=True) as client:
        response = await client.get(target_url, headers=headers, timeout=10.0)
        
        if response.status_code != 200:
          Logger.error(f"Pathfinder API returned {response.status_code}")
          return -1
        
        data = response.json()
        # Handle list or dict response
        connections_list = data.get('connections', []) if isinstance(data, dict) else data
        
        if not isinstance(connections_list, list):
          Logger.error("Pathfinder API response format not recognized")
          return -1

        count = 0
        for conn in connections_list:
          if self._process_connection(conn, solar_map):
            count += 1
        return count

    except Exception as e:
      Logger.error(f"Failed to fetch Pathfinder data: {e}")
      return -1

  def _process_connection(self, conn: Dict[str, Any], solar_map: SolarMap) -> bool:
    try:
      # Extract IDs
      source_id = int(conn.get('source', 0))
      dest_id = int(conn.get('target', 0))
      
      if source_id == 0 or dest_id == 0:
        return False

      # Signatures & Type
      sig_source = conn.get('source_sig', '???')
      sig_dest = conn.get('target_sig', '???')
      wh_type = conn.get('type', 'K162')
      
      # Life & Mass
      life_str = str(conn.get('life', 'stable')).lower()
      mass_str = str(conn.get('mass', 'stable')).lower()
      
      wh_life = WormholeTimespan.STABLE
      if 'crit' in life_str:
        wh_life = WormholeTimespan.CRITICAL
        
      wh_mass = WormholeMassspan.STABLE
      if 'destab' in mass_str:
        wh_mass = WormholeMassspan.DESTAB
      elif 'crit' in mass_str:
        wh_mass = WormholeMassspan.CRITICAL
        
      # Size
      wh_size = self.eve_db.get_whsize_by_code(wh_type)
      if not WormholeSize.valid(wh_size):
         size_str = str(conn.get('size', '')).lower()
         if 'xl' in size_str: wh_size = WormholeSize.XLARGE
         elif 'large' in size_str: wh_size = WormholeSize.LARGE
         elif 'medium' in size_str: wh_size = WormholeSize.MEDIUM
         elif 'small' in size_str: wh_size = WormholeSize.SMALL
         else:
            wh_size = self.eve_db.get_whsize_by_system(source_id, dest_id)

      # Time elapsed
      updated_at_str = conn.get('updated_at')
      time_elapsed = 0.0
      if updated_at_str:
        try:
          # Handle ISO format (e.g. 2023-10-27T10:00:00Z)
          if 'Z' in updated_at_str:
             updated_at_str = updated_at_str.replace('Z', '+00:00')
          updated_at = datetime.fromisoformat(updated_at_str)
          if updated_at.tzinfo is None:
             updated_at = updated_at.replace(tzinfo=timezone.utc)
          
          delta = datetime.now(timezone.utc) - updated_at
          time_elapsed = round(delta.total_seconds() / 3600.0, 1)
        except ValueError:
          pass

      solar_map.add_connection(
        source_id,
        dest_id,
        ConnectionType.WORMHOLE,
        [
          sig_source,
          wh_type,
          sig_dest,
          'K162',
          wh_size,
          wh_life,
          wh_mass,
          time_elapsed,
          "Pathfinder",
        ],
      )
      return True
    except Exception as e:
      Logger.error(f"Error processing Pathfinder connection: {e}")
      return False

  def augment_map(self, solar_map: SolarMap) -> int:
    return asyncio.run(self._augment_map_async(solar_map))