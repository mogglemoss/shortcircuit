from typing import Dict, Any, Tuple
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
        self._wanderer.source_id = self.id

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value.strip().rstrip('/') if value else ""
        if self._url and not (self._url.startswith('http://') or self._url.startswith('https://')):
            self._url = 'https://' + self._url
        if hasattr(self, '_wanderer'):
            self._wanderer.url = self._url

    @property
    def map_id(self):
        return self._map_id

    @map_id.setter
    def map_id(self, value):
        self._map_id = value
        if hasattr(self, '_wanderer'):
            self._wanderer.map_id = value

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        if hasattr(self, '_wanderer'):
            self._wanderer.token = value
            # Update headers in Wanderer instance
            self._wanderer.headers["Authorization"] = f"Bearer {value}"

    @property
    def type(self) -> SourceType:
        return SourceType.WANDERER

    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map."""
        if not self.enabled:
            return 0
            
        return self._wanderer.augment_map(solar_map)

    def fetch_test_data(self) -> int:
        """Fetch data for testing purposes, without modifying the SolarMap."""
        return self._wanderer.augment_map(SolarMap(None))

    def connect(self) -> Tuple[bool, str]:
        """Test connection or authenticate."""
        return self._wanderer.test_credentials()

    def get_status(self) -> str:
        """Get current connection status."""
        success, _ = self.connect()
        return "Connected" if success else "Disconnected"

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
