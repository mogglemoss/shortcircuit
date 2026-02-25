from abc import ABC, abstractmethod
import uuid
from enum import Enum
from typing import Dict, Any
from shortcircuit.model.solarmap import SolarMap

class SourceType(str, Enum):
    TRIPWIRE = "tripwire"
    WANDERER = "wanderer"
    PATHFINDER = "pathfinder"
    EVESCOUT = "evescout"

class MapSource(ABC):
    def __init__(self, id: str = None, name: str = "", enabled: bool = True):
        self.id = id if id else str(uuid.uuid4())
        self.name = name
        self.enabled = enabled

    @property
    @abstractmethod
    def type(self) -> SourceType:
        pass

    @abstractmethod
    def fetch_data(self, solar_map: SolarMap) -> int:
        """Fetch data and augment the provided solar map. Returns number of connections added."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Test connection or authenticate."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Get current connection status."""
        pass

    @abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """Serialize source config to dict."""
        pass

    @classmethod
    @abstractmethod
    def from_json(cls, data: Dict[str, Any]) -> 'MapSource':
        """Deserialize source config from dict."""
        pass
