import json
from unittest.mock import MagicMock, patch
import pytest
from shortcircuit.model.source_manager import SourceManager
from shortcircuit.model.mapsource import SourceType
from shortcircuit.model.tripwire_source import TripwireSource
from shortcircuit.model.wanderer_source import WandererSource
from shortcircuit.model.pathfinder_source import PathfinderSource
from shortcircuit.model.evescout_source import EveScoutSource

@pytest.fixture
def source_manager():
    # Reset singleton for testing
    SourceManager._instance = None
    sm = SourceManager()
    # Register classes because load_configuration depends on them for instantiation
    sm.register_source_class(SourceType.TRIPWIRE, TripwireSource)
    sm.register_source_class(SourceType.WANDERER, WandererSource)
    sm.register_source_class(SourceType.PATHFINDER, PathfinderSource)
    sm.register_source_class(SourceType.EVESCOUT, EveScoutSource)
    return sm

def test_legacy_migration(source_manager):
    mock_settings = MagicMock()
    
    # Setup legacy values as they would appear in QSettings
    legacy_values = {
        "MapSources": None,
        "tripwire_url": "http://tw.com",
        "tripwire_user": "tw_user",
        "tripwire_pass": "tw_pass",
        "Tripwire/url": "http://tw-alt.com",
        "Tripwire/username": "tw_user_alt",
        "Tripwire/password": "tw_pass_alt",
        "Wanderer/url": "http://wand.com",
        "Wanderer/map_id": "123",
        "Wanderer/token": "abc",
        "eve_scout_enable": "true",
        "Pathfinder/url": "http://pf.com",
        "Pathfinder/token": "pf_token",
        "Pathfinder/enabled": "true"
    }
    
    # Mock the value() method to return our legacy data
    mock_settings.value.side_effect = lambda key, default=None: legacy_values.get(key, default)
    
    with patch('shortcircuit.model.source_manager.Configuration') as mock_config:
        mock_config.settings = mock_settings
        
        # Trigger migration
        source_manager.load_configuration()
        
        # 1. Verify sources were created in memory
        sources = source_manager.get_sources()
        assert len(sources) == 5
        
        # Verify Tripwire migration
        tw = next(s for s in sources if s.type == SourceType.TRIPWIRE)
        assert tw.url == "http://tw.com"
        assert tw.username == "tw_user"
        assert tw.password == "tw_pass"

        tw_alt = next(s for s in sources if s.type == SourceType.TRIPWIRE and s.name == "Legacy Tripwire (Alt)")
        assert tw_alt.url == "http://tw-alt.com"
        assert tw_alt.username == "tw_user_alt"
        assert tw_alt.password == "tw_pass_alt"
        
        # Verify Wanderer migration
        wand = next(s for s in sources if s.type == SourceType.WANDERER)
        assert wand.url == "http://wand.com"
        assert wand.map_id == "123"
        assert wand.token == "abc"
        
        # Verify EveScout migration
        es = next(s for s in sources if s.type == SourceType.EVESCOUT)
        assert es.enabled is True
        
        # Verify Pathfinder migration
        pf = next(s for s in sources if s.type == SourceType.PATHFINDER)
        assert pf.url == "http://pf.com"
        assert pf.token == "pf_token"
        assert pf.enabled is True
        
        # 2. Verify legacy keys were removed from settings
        mock_settings.remove.assert_any_call("tripwire_url")
        mock_settings.remove.assert_any_call("tripwire_user")
        mock_settings.remove.assert_any_call("tripwire_pass")
        mock_settings.remove.assert_any_call("Tripwire/url")
        mock_settings.remove.assert_any_call("Tripwire/username")
        mock_settings.remove.assert_any_call("Tripwire/password")
        mock_settings.remove.assert_any_call("Wanderer/url")
        mock_settings.remove.assert_any_call("Wanderer/map_id")
        mock_settings.remove.assert_any_call("Wanderer/token")
        mock_settings.remove.assert_any_call("eve_scout_enable")
        mock_settings.remove.assert_any_call("Pathfinder/url")
        mock_settings.remove.assert_any_call("Pathfinder/token")
        mock_settings.remove.assert_any_call("Pathfinder/enabled")
            
        # 3. Verify new configuration was saved in the new JSON format
        mock_settings.setValue.assert_called()
        args, _ = mock_settings.setValue.call_args
        assert args[0] == "MapSources"
        
        # Verify that the saved JSON can be re-loaded
        saved_json = args[1]
        legacy_values["MapSources"] = saved_json
        source_manager.sources = []
        source_manager.load_configuration()
        
        reloaded_sources = source_manager.get_sources()
        assert len(reloaded_sources) == 5
        assert reloaded_sources[0].name == tw.name
        assert reloaded_sources[1].name == tw_alt.name
        assert reloaded_sources[2].name == wand.name