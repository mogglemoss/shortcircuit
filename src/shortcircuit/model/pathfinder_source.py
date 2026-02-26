from typing import Dict, Any, Tuple
from shortcircuit.model.mapsource import MapSource, SourceType
from shortcircuit.model.pathfinder import Pathfinder
from shortcircuit.model.solarmap import SolarMap

class PathfinderSource(MapSource):
    def __init__(self, id: str = None, name: str = "Pathfinder", enabled: bool = True, url: str = "", token: str = ""):
        super().__init__(id, name, enabled)
        self.url = url
        self.token = token
        self._pathfinder = Pathfinder(url=self.url, token=self.token, name=name)
        self._pathfinder.source_id = self.id

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value.strip().rstrip('/') if value else ""
        if self._url and not (self._url.startswith('http://') or self._url.startswith('https://')):
            self._url = 'https://' + self._url
        if hasattr(self, '_pathfinder'):
            self._pathfinder.url = self._url

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        if hasattr(self, '_pathfinder'):
            self._pathfinder.token = value

    @property
    def type(self) -> SourceType:
        return SourceType.PATHFINDER

    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map."""
        if not self.enabled:
            return 0
            
        return self._pathfinder.augment_map(solar_map)

    def connect(self) -> Tuple[bool, str]:
        """Test connection or authenticate."""
        return self._pathfinder.test_credentials()

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
                "token": self.token,
            }
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'PathfinderSource':
        """Deserialize source config from dict."""
        config = data.get("config", {})
        return cls(
            id=data.get("id"),
            name=data.get("name", "Pathfinder"),
            enabled=data.get("enabled", True),
            url=config.get("url", ""),
            token=config.get("token", "")
        )
