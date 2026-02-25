from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from shortcircuit.model.solarmap import ConnectionType
from shortcircuit.model.evedb import WormholeSize, WormholeTimespan, WormholeMassspan

@dataclass
class ConnectionData:
    source_id: str
    source_system: int
    dest_system: int
    con_type: ConnectionType
    
    # Wormhole specific
    sig_source: Optional[str] = None
    code_source: Optional[str] = None
    sig_dest: Optional[str] = None
    code_dest: Optional[str] = None
    wh_size: int = WormholeSize.UNKNOWN
    wh_life: int = WormholeTimespan.STABLE
    wh_mass: int = WormholeMassspan.STABLE
    time_elapsed: float = 0.0  # Age in hours (lower is fresher)
    source_name: Optional[str] = None
    
    updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


class ConnectionDB:
    """
    In-memory database for storing connections from multiple map sources.
    Handles deduplication and conflict resolution at query time.
    """
    def __init__(self):
        # Maps (source_system, dest_system) -> Dict[source_id, ConnectionData]
        self._connections: Dict[Tuple[int, int], Dict[str, ConnectionData]] = {}

    def add_connection(self, data: ConnectionData):
        key = (data.source_system, data.dest_system)
        if key not in self._connections:
            self._connections[key] = {}
        self._connections[key][data.source_id] = data

    def remove_connection(self, source_system: int, dest_system: int, source_id: str):
        key = (source_system, dest_system)
        if key in self._connections and source_id in self._connections[key]:
            del self._connections[key][source_id]
            if not self._connections[key]:
                del self._connections[key]

    def clear_source(self, source_id: str):
        """Remove all connections from a specific source."""
        empty_keys = []
        for key, sources_dict in self._connections.items():
            if source_id in sources_dict:
                del sources_dict[source_id]
                if not sources_dict:
                    empty_keys.append(key)
        for key in empty_keys:
            del self._connections[key]

    def get_resolved_connections(self, max_age_hours: float = 48.0) -> List[ConnectionData]:
        """
        Returns a deduplicated list of connections.
        Conflict resolution:
        1. Gates always win over Wormholes.
        2. Fresher data (lower time_elapsed) wins.
        3. If same age, healthier status wins.
        """
        resolved = []
        for (src, dst), sources_dict in self._connections.items():
            best_conn = None
            
            for conn in sources_dict.values():
                # Filter out stale connections based on our internal DB timestamp or age
                # (Assuming time_elapsed is the primary age indicator provided by sources)
                if conn.time_elapsed > max_age_hours:
                    continue
                
                if best_conn is None:
                    best_conn = conn
                    continue
                
                # Gates take precedence
                if conn.con_type == ConnectionType.GATE and best_conn.con_type != ConnectionType.GATE:
                    best_conn = conn
                    continue
                if best_conn.con_type == ConnectionType.GATE and conn.con_type != ConnectionType.GATE:
                    continue
                    
                # If both are wormholes or both are gates
                if conn.con_type == ConnectionType.WORMHOLE:
                    if conn.time_elapsed < best_conn.time_elapsed:
                        best_conn = conn
                    elif conn.time_elapsed == best_conn.time_elapsed:
                        # Tie-breaker: Health (Stable < Critical)
                        # WormholeTimespan: STABLE=0, CRITICAL=1
                        if conn.wh_life < best_conn.wh_life:
                            best_conn = conn
                            
            if best_conn:
                resolved.append(best_conn)
                
        return resolved
