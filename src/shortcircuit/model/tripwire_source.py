from typing import Dict, Any
from shortcircuit.model.mapsource import MapSource, SourceType
from shortcircuit.model.tripwire import Tripwire
from shortcircuit.model.solarmap import SolarMap

class TripwireSource(MapSource):
    def __init__(self, id: str = None, name: str = "Tripwire", enabled: bool = True, url: str = "", username: str = "", password: str = ""):
        super().__init__(id, name, enabled)
        self.url = url
        self.username = username
        self.password = password
        self._tripwire = Tripwire(username, password, url, name)

    @property
    def type(self) -> SourceType:
        return SourceType.TRIPWIRE

    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map."""
        if not self.enabled:
            return 0
            
        # Temporarily tell the tripwire instance its name so connections are tagged correctly
        self._tripwire.name = self.id
        
        connections_added = self._tripwire.augment_map(solar_map)
        
        # Restore actual name
        self._tripwire.name = self.name
        
        return connections_added

    def connect(self) -> bool:
        """Test connection or authenticate."""
        success, _ = self._tripwire.test_credentials()
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
                "username": self.username,
                "password": self.password,
            }
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'TripwireSource':
        """Deserialize source config from dict."""
        config = data.get("config", {})
        return cls(
            id=data.get("id"),
            name=data.get("name", "Tripwire"),
            enabled=data.get("enabled", True),
            url=config.get("url", ""),
            username=config.get("username", ""),
            password=config.get("password", "")
        )
