import json
from datetime import datetime
from typing import List, Dict, Type

from PySide6 import QtCore
from shortcircuit.model.mapsource import MapSource, SourceType
from shortcircuit.model.solarmap import SolarMap
from shortcircuit.model.utility.configuration import Configuration
from shortcircuit.model.logger import Logger
from shortcircuit.model.utility.singleton import Singleton

# Combined metaclass to avoid conflict with QObject's metaclass
class SingletonQObject(type(QtCore.QObject), Singleton):
    pass

class SourceManager(QtCore.QObject, metaclass=SingletonQObject):
    sources_changed = QtCore.Signal()

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._initialized = True
        self.sources = []
        self._registry = {}

    def register_source_class(self, source_type: SourceType, source_class: Type[MapSource]):
        self._registry[source_type] = source_class

    def add_source(self, source: MapSource):
        self.sources.append(source)
        self.save_configuration()

    def remove_source(self, source_id: str):
        self.sources = [s for s in self.sources if s.id != source_id]
        self.save_configuration()

    def get_sources(self) -> List[MapSource]:
        return self.sources

    def get_enabled_sources(self) -> List[MapSource]:
        return [s for s in self.sources if s.enabled]

    def fetch_all(self, solar_map: SolarMap) -> Dict[str, int]:
        results = {}
        for source in self.get_enabled_sources():
            try:
                # Clear existing data from this source before fetching new
                solar_map.connection_db.clear_source(source.id)
                count = source.fetch_data(solar_map)
                results[source.name] = count
                if count >= 0:
                    source.last_updated = datetime.now()
            except Exception as e:
                Logger.error(f"Error fetching data from source {source.name}: {e}")
                results[source.name] = -1
        
        # Mark graph as dirty so it gets rebuilt on next query
        solar_map._graph_dirty = True
        self.sources_changed.emit()
        return results

    def fetch_one(self, source_id: str, solar_map: SolarMap) -> Dict[str, int]:
        """Fetch data from a single specific source."""
        results = {}
        source = next((s for s in self.sources if s.id == source_id), None)
        if source and source.enabled:
            try:
                # Clear existing data from this source before fetching new
                solar_map.connection_db.clear_source(source.id)
                count = source.fetch_data(solar_map)
                results[source.name] = count
                if count >= 0:
                    source.last_updated = datetime.now()
            except Exception as e:
                Logger.error(f"Error fetching data from source {source.name}: {e}")
                results[source.name] = -1
        
        solar_map._graph_dirty = True
        self.sources_changed.emit()
        return results

    def load_configuration(self):
        self.sources = []
        settings = Configuration.settings
        
        # Check for new format first
        json_data = settings.value("MapSources")
        if json_data:
            try:
                sources_data = json.loads(json_data)
                for data in sources_data:
                    source_type_str = data.get("type")
                    if not source_type_str:
                        continue
                        
                    source_type = SourceType(source_type_str)
                    if source_type in self._registry:
                        source_class = self._registry[source_type]
                        source = source_class.from_json(data)
                        self.sources.append(source)
            except Exception as e:
                Logger.error(f"Failed to load MapSources: {e}")

        # If empty, check for legacy migration
        if not self.sources:
            self._migrate_legacy_configuration()
        else:
            self.sources_changed.emit()

    def _migrate_legacy_configuration(self):
        settings = Configuration.settings
        migrated = False
        
        # Legacy Tripwire (Flat)
        tw_url = settings.value("tripwire_url", "")
        tw_user = settings.value("tripwire_user", "")
        tw_pass = settings.value("tripwire_pass", "")
        if tw_url and tw_user and SourceType.TRIPWIRE in self._registry:
            source_class = self._registry[SourceType.TRIPWIRE]
            Logger.info("Migrating legacy Tripwire configuration (flat).")
            self.sources.append(source_class(name="Legacy Tripwire", url=tw_url, username=tw_user, password=tw_pass))
            migrated = True
            settings.remove("tripwire_url")
            settings.remove("tripwire_user")
            settings.remove("tripwire_pass")

        # Legacy Tripwire (Grouped)
        tw_url = settings.value("Tripwire/url", "")
        tw_user = settings.value("Tripwire/username", "")
        tw_pass = settings.value("Tripwire/password", "")
        if tw_url and tw_user and SourceType.TRIPWIRE in self._registry:
            source_class = self._registry[SourceType.TRIPWIRE]
            Logger.info("Migrating legacy Tripwire configuration (grouped).")
            self.sources.append(source_class(name="Legacy Tripwire (Alt)", url=tw_url, username=tw_user, password=tw_pass))
            migrated = True
            settings.remove("Tripwire/url")
            settings.remove("Tripwire/username")
            settings.remove("Tripwire/password")
            
        # Legacy Wanderer
        wand_map = settings.value("Wanderer/map_id", "")
        wand_token = settings.value("Wanderer/token", "")
        if wand_map and wand_token and SourceType.WANDERER in self._registry:
            source_class = self._registry[SourceType.WANDERER]
            
            # Flat URL
            wand_url = settings.value("wanderer_url", "")
            if wand_url:
                Logger.info("Migrating legacy Wanderer configuration (flat).")
                self.sources.append(source_class(name="Legacy Wanderer", url=wand_url, map_id=wand_map, token=wand_token))
                migrated = True
                settings.remove("wanderer_url")
            
            # Grouped URL
            wand_url = settings.value("Wanderer/url", "")
            if wand_url:
                Logger.info("Migrating legacy Wanderer configuration (grouped).")
                self.sources.append(source_class(name="Legacy Wanderer (Alt)", url=wand_url, map_id=wand_map, token=wand_token))
                migrated = True
                settings.remove("Wanderer/url")
                
            if migrated:
                settings.remove("Wanderer/map_id")
                settings.remove("Wanderer/token")

        # Legacy EveScout
        for es_key in ["eve_scout_enable", "Tripwire/evescout_enabled"]:
            es_enabled = settings.value(es_key, "false")
            if es_enabled.lower() == "true" and SourceType.EVESCOUT in self._registry:
                source_class = self._registry[SourceType.EVESCOUT]
                Logger.info(f"Migrating legacy EveScout configuration ({es_key}).")
                self.sources.append(source_class(name="Eve Scout" if es_key == "eve_scout_enable" else "Eve Scout (Alt)", enabled=True))
                migrated = True
                settings.remove(es_key)

        # Legacy Pathfinder
        if SourceType.PATHFINDER in self._registry:
            pf_url = settings.value("Pathfinder/url", "")
            pf_token = settings.value("Pathfinder/token", "")
            if pf_url and pf_token:
                source_class = self._registry[SourceType.PATHFINDER]
                Logger.info("Migrating legacy Pathfinder configuration.")
                pf_enabled = settings.value("Pathfinder/enabled", "false").lower() == "true"
                self.sources.append(source_class(name="Legacy Pathfinder", url=pf_url, token=pf_token, enabled=pf_enabled))
                migrated = True
                settings.remove("Pathfinder/url")
                settings.remove("Pathfinder/token")
                settings.remove("Pathfinder/enabled")
            
        if migrated:
            self.save_configuration()

    def save_configuration(self):
        settings = Configuration.settings
        data = [s.to_json() for s in self.sources]
        settings.setValue("MapSources", json.dumps(data))
        self.sources_changed.emit()
