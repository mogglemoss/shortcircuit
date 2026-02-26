from typing import Dict, Any, Tuple
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
        self._tripwire.source_id = self.id

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value.strip().rstrip('/') if value else ""
        if self._url and not (self._url.startswith('http://') or self._url.startswith('https://')):
            self._url = 'https://' + self._url
        if hasattr(self, '_tripwire'):
            self._tripwire.url = self._url

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value
        if hasattr(self, '_tripwire'):
            self._tripwire.username = value

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value
        if hasattr(self, '_tripwire'):
            self._tripwire.password = value

    @property
    def type(self) -> SourceType:
        return SourceType.TRIPWIRE

    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map."""
        if not self.enabled:
            return 0
            
        return self._tripwire.augment_map(solar_map)

    def connect(self) -> Tuple[bool, str]:
        """Test connection or authenticate."""
        return self._tripwire.test_credentials()

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
