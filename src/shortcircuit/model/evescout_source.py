from typing import Dict, Any, Tuple
from shortcircuit.model.mapsource import MapSource, SourceType
from shortcircuit.model.evescout import EveScout
from shortcircuit.model.solarmap import SolarMap

class EveScoutSource(MapSource):
    def __init__(self, id: str = None, name: str = "Eve Scout", enabled: bool = True, url: str = "https://api.eve-scout.com/v2/public/signatures"):
        super().__init__(id, name, enabled)
        self.url = url
        self._evescout = EveScout(url=self.url, name=name)
        self._evescout.source_id = self.id

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value.strip().rstrip('/') if value else ""
        if self._url and not (self._url.startswith('http://') or self._url.startswith('https://')):
            self._url = 'https://' + self._url
        if hasattr(self, '_evescout'):
            self._evescout.evescout_url = self._url

    @property
    def type(self) -> SourceType:
        return SourceType.EVESCOUT

    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map."""
        if not self.enabled:
            return 0
            
        return self._evescout.augment_map(solar_map)

    def connect(self) -> Tuple[bool, str]:
        """EveScout doesn't require authentication, just return True if URL is set."""
        if self.url:
            return True, "URL is set."
        return False, "URL is missing."

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
            }
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'EveScoutSource':
        """Deserialize source config from dict."""
        config = data.get("config", {})
        return cls(
            id=data.get("id"),
            name=data.get("name", "Eve Scout"),
            enabled=data.get("enabled", True),
            url=config.get("url", "https://api.eve-scout.com/v2/public/signatures")
        )
