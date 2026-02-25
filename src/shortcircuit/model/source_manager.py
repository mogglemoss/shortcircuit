import json
from typing import List, Dict, Type

from shortcircuit.model.mapsource import MapSource, SourceType
from shortcircuit.model.solarmap import SolarMap
from shortcircuit.model.utility.configuration import Configuration
from shortcircuit.model.logger import Logger

class SourceManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SourceManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.sources = []
            cls._instance._registry = {}
        return cls._instance

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
            except Exception as e:
                Logger.error(f"Error fetching data from source {source.name}: {e}")
                results[source.name] = -1
        
        # Mark graph as dirty so it gets rebuilt on next query
        solar_map._graph_dirty = True
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

    def _migrate_legacy_configuration(self):
        settings = Configuration.settings
        migrated = False
        
        # Legacy Tripwire
        tw_url = settings.value("tripwire_url", "")
        if not tw_url:
            tw_url = settings.value("Tripwire/url", "")
            
        tw_user = settings.value("tripwire_user", "")
        if not tw_user:
            tw_user = settings.value("Tripwire/username", "")
            
        tw_pass = settings.value("tripwire_pass", "")
        if not tw_pass:
            tw_pass = settings.value("Tripwire/password", "")
        
        if tw_url and tw_user and SourceType.TRIPWIRE in self._registry:
            source_class = self._registry[SourceType.TRIPWIRE]
            Logger.info("Migrating legacy Tripwire configuration.")
            
            source = source_class(name="Legacy Tripwire", url=tw_url, username=tw_user, password=tw_pass)
            self.sources.append(source)
            migrated = True
            
            # Clean up old settings
            settings.remove("tripwire_url")
            settings.remove("tripwire_user")
            settings.remove("tripwire_pass")
            settings.remove("Tripwire/url")
            settings.remove("Tripwire/username")
            settings.remove("Tripwire/password")
            
        # Legacy Wanderer
        wand_url = settings.value("wanderer_url", "")
        if not wand_url:
            wand_url = settings.value("Wanderer/url", "")
            
        wand_map = settings.value("Wanderer/map_id", "")
        wand_token = settings.value("Wanderer/token", "")
            
        if wand_url and wand_map and wand_token and SourceType.WANDERER in self._registry:
            source_class = self._registry[SourceType.WANDERER]
            Logger.info("Migrating legacy Wanderer configuration.")
            
            source = source_class(name="Legacy Wanderer", url=wand_url, map_id=wand_map, token=wand_token)
            self.sources.append(source)
            migrated = True
            
            # Clean up old settings
            settings.remove("wanderer_url")
            settings.remove("Wanderer/url")
            settings.remove("Wanderer/map_id")
            settings.remove("Wanderer/token")

        # Legacy EveScout
        es_enabled = settings.value("eve_scout_enable", "false")
        if es_enabled.lower() != "true":
            es_enabled = settings.value("Tripwire/evescout_enabled", "false")
            
        if es_enabled.lower() == "true" and SourceType.EVESCOUT in self._registry:
            source_class = self._registry[SourceType.EVESCOUT]
            Logger.info("Migrating legacy EveScout configuration.")
            
            source = source_class(name="Eve Scout", enabled=True)
            self.sources.append(source)
            migrated = True
            
            # Clean up old settings
            settings.remove("eve_scout_enable")
            settings.remove("Tripwire/evescout_enabled")

        # Legacy Pathfinder
        pf_url = settings.value("Pathfinder/url", "")
        pf_token = settings.value("Pathfinder/token", "")
            
        if pf_url and pf_token and SourceType.PATHFINDER in self._registry:
            source_class = self._registry[SourceType.PATHFINDER]
            Logger.info("Migrating legacy Pathfinder configuration.")
            
            pf_enabled = settings.value("Pathfinder/enabled", "false").lower() == "true"
            source = source_class(name="Legacy Pathfinder", url=pf_url, token=pf_token, enabled=pf_enabled)
            self.sources.append(source)
            migrated = True
            
            # Clean up old settings
            settings.remove("Pathfinder/url")
            settings.remove("Pathfinder/token")
            settings.remove("Pathfinder/enabled")
            
        if migrated:
            self.save_configuration()

    def save_configuration(self):
        settings = Configuration.settings
        data = [s.to_json() for s in self.sources]
        settings.setValue("MapSources", json.dumps(data))
