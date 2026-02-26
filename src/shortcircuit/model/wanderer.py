# wanderer.py

import asyncio
import json
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, List, TYPE_CHECKING

import httpx
from .evedb import EveDb, WormholeSize, WormholeMassspan, WormholeTimespan
from .logger import Logger
from .solarmap import ConnectionType, SolarMap

if TYPE_CHECKING:
  from shortcircuit.model.connection_db import ConnectionData

class Wanderer:
  def __init__(self, url: str, map_id: str, token: str, name: str = "Wanderer"):
    self.url = url.strip().rstrip('/') if url else ""
    if self.url and not (self.url.startswith('http://') or self.url.startswith('https://')):
      self.url = 'https://' + self.url
    self.map_id = map_id
    self.token = token
    self.name = name
    self.source_id = name
    self.headers = {
      "Authorization": f"Bearer {self.token}",
      "Accept": "application/json"
    }
    self.eve_db = EveDb()

  def get_name(self) -> str:
    return self.name

  def test_credentials(self) -> Tuple[bool, str]:
    return asyncio.run(self._test_credentials_async())

  async def _test_credentials_async(self) -> Tuple[bool, str]:
    if not self.url or not self.map_id or not self.token:
      return False, "Missing URL, Map ID, or Token"

    try:
      # Endpoint: /api/maps/{map_id}/signatures
      api_url = f"{self.url}/api/maps/{self.map_id}/signatures"
      async with httpx.AsyncClient(verify=True) as client:
        response = await client.get(api_url, headers=self.headers, timeout=10, follow_redirects=True)

        if response.status_code == 200:
          return True, "Connection successful"
        elif response.status_code == 401:
          return False, "Unauthorized: Check your token"
        elif response.status_code == 404:
          return False, "Map not found or invalid URL"
        else:
          return False, f"HTTP Error: {response.status_code}"
    except httpx.RequestError as e:
      return False, f"Connection error: {e}"
    except Exception as e:
      return False, f"Error: {e}"

  async def _get_signatures_async(self) -> Optional[List[Dict]]:
    if not self.url or not self.map_id or not self.token:
      return None

    try:
      api_url = f"{self.url}/api/maps/{self.map_id}/signatures"
      async with httpx.AsyncClient(verify=True) as client:
        response = await client.get(api_url, headers=self.headers, timeout=10, follow_redirects=True)
        if response.status_code == 200:
          data = response.json()
          return data.get('data', [])
        else:
          Logger.error(f"Wanderer API error: {response.status_code}")
          return None
    except Exception as e:
      Logger.error(f"Wanderer connection error: {e}")
      return None

  def augment_map(self, solar_map: SolarMap) -> int:
    return asyncio.run(self._augment_map_async(solar_map))

  async def _augment_map_async(self, solar_map: SolarMap) -> int:
    signatures = await self._get_signatures_async()
    if signatures is None:
      return -1

    connections_added = 0

    for sig in signatures:
      # Filter for wormholes
      if sig.get('group') != 'Wormhole':
        continue

      # We need a linked system to form a connection
      system_id = sig.get('solar_system_id')
      linked_system_id = sig.get('linked_system_id')

      if not system_id or not linked_system_id:
        continue
      
      # Ensure IDs are ints
      try:
        system_id = int(system_id)
        linked_system_id = int(linked_system_id)
      except (ValueError, TypeError):
        continue

      # Parse custom_info
      time_status = 1  # Default stable
      mass_status = 1  # Default stable
      
      custom_info_str = sig.get('custom_info')
      if custom_info_str:
        try:
          if isinstance(custom_info_str, str):
            custom_info = json.loads(custom_info_str)
          else:
            custom_info = custom_info_str
          
          if isinstance(custom_info, dict):
            time_status = int(custom_info.get('time_status', 1))
            mass_status = int(custom_info.get('mass_status', 1))
        except Exception:
            pass

      # Map status to enums
      # Wanderer Time: 1=Stable, 2=EOL
      wh_life = WormholeTimespan.CRITICAL if time_status == 2 else WormholeTimespan.STABLE
      
      # Wanderer Mass: 1=Stable, 2=Destab, 3=Critical
      wh_mass = WormholeMassspan.STABLE
      if mass_status == 2:
        wh_mass = WormholeMassspan.DESTAB
      elif mass_status == 3:
        wh_mass = WormholeMassspan.CRITICAL

      # Type and Size
      wh_type = sig.get('type')
      if not wh_type:
        wh_type = '????'
      
      wh_size = self.eve_db.get_whsize_by_code(wh_type)
      if not WormholeSize.valid(wh_size):
        wh_size = self.eve_db.get_whsize_by_system(system_id, linked_system_id)

      # Signature ID
      sig_id = sig.get('eve_id', '???')
      
      # Time elapsed
      updated_at_str = sig.get('updated_at')
      time_elapsed = 0.0
      if updated_at_str:
        try:
          if updated_at_str.endswith('Z'):
             updated_at_str = updated_at_str[:-1] + '+00:00'
          updated_at = datetime.fromisoformat(updated_at_str)
          delta = datetime.now(timezone.utc) - updated_at
          time_elapsed = round(delta.total_seconds() / 3600.0, 1)
        except Exception:
          pass

      # Add connection
      wh_type_out = 'K162' if wh_type != '????' and wh_type != 'K162' else '????'
      
      from shortcircuit.model.connection_db import ConnectionData
      solar_map.add_connection(
        ConnectionData(
          source_id=self.source_id,
          source_system=system_id,
          dest_system=linked_system_id,
          con_type=ConnectionType.WORMHOLE,
          sig_source=sig_id,
          code_source=wh_type,
          sig_dest='???',
          code_dest=wh_type_out,
          wh_size=wh_size,
          wh_life=wh_life,
          wh_mass=wh_mass,
          time_elapsed=time_elapsed,
          source_name=self.name
        )
      )
      connections_added += 1

    return connections_added