from typing import Dict, Any
from shortcircuit.model.mapsource import MapSource, SourceType
from shortcircuit.model.wanderer import Wanderer
from shortcircuit.model.solarmap import SolarMap

class WandererSource(MapSource):
    def __init__(self, id: str = None, name: str = "Wanderer", enabled: bool = True, url: str = "", map_id: str = "", token: str = ""):
        super().__init__(id, name, enabled)
        self.url = url
        self.map_id = map_id
        self.token = token
        self._wanderer = Wanderer(url, map_id, token)
        self._wanderer.name = name

    @property
    def type(self) -> SourceType:
        return SourceType.WANDERER

    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map."""
        if not self.enabled:
            return 0
            
        # Temporarily tell the wanderer instance its name so connections are tagged correctly
        self._wanderer.name = self.id
        
        connections_added = self._wanderer.augment_map(solar_map)
        
        # Restore actual name
        self._wanderer.name = self.name
        
        return connections_added

    def connect(self) -> bool:
        """Test connection or authenticate."""
        success, _ = self._wanderer.test_credentials()
        return success

    def get_status(self) -> str:
        """Get current connection status."""
        return "Connected" if self.connect() else "Disconnected"

    def to_json(self) -> Dict[str, Any]:
        """Serialize source config to dict."""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "enabled": self.enabled,
            "config": {
                "url": self.url,
                "map_id": self.map_id,
                "token": self.token,
            }
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'WandererSource':
        """Deserialize source config from dict."""
        config = data.get("config", {})
        return cls(
            id=data.get("id"),
            name=data.get("name", "Wanderer"),
            enabled=data.get("enabled", True),
            url=config.get("url", ""),
            map_id=config.get("map_id", ""),
            token=config.get("token", "")
        )
