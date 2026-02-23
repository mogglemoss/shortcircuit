# src/shortcircuit/model/test_pathfinder.py

from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import pytest

from shortcircuit.model.pathfinder import Pathfinder
from shortcircuit.model.solarmap import SolarMap, ConnectionType
from shortcircuit.model.evedb import EveDb, WormholeSize, WormholeTimespan, WormholeMassspan

class TestPathfinder:
    def setup_method(self):
        self.pathfinder = Pathfinder("https://pathfinder.example.com", "test_token")
        # Mock EveDb to avoid loading CSVs
        self.pathfinder.eve_db = Mock(spec=EveDb)
        self.pathfinder.eve_db.get_whsize_by_code.return_value = WormholeSize.UNKNOWN
        self.pathfinder.eve_db.get_whsize_by_system.return_value = WormholeSize.UNKNOWN
        
        self.solar_map = Mock(spec=SolarMap)

    @patch('httpx.AsyncClient')
    def test_augment_map_parses_dict_response(self, mock_client_cls):
        """Test parsing when API returns a dict with 'connections' key"""
        # Setup mock client
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_response = Mock()
        # Explicitly set status_code as an integer, not a Mock
        mock_response.status_code = 200
        
        # Mock data
        mock_data = {
            "connections": [
                {
                    "source": "30000142",
                    "target": "31000005",
                    "source_sig": "ABC",
                    "target_sig": "DEF",
                    "type": "K162",
                    "life": "stable",
                    "mass": "stable",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        mock_response.json.return_value = mock_data
        mock_client.get.return_value = mock_response

        # Configure EveDb mock
        self.pathfinder.eve_db.get_whsize_by_code.return_value = WormholeSize.LARGE

        # Execute
        count = self.pathfinder.augment_map(self.solar_map)

        # Verify
        assert count == 1
        self.solar_map.add_connection.assert_called_once()
        
        args = self.solar_map.add_connection.call_args[0]
        assert args[0] == 30000142
        assert args[1] == 31000005
        assert args[2] == ConnectionType.WORMHOLE
        
        info = args[3]
        assert info[0] == "ABC"
        assert info[1] == "K162"
        assert info[2] == "DEF"
        assert info[3] == "K162"
        assert info[4] == WormholeSize.LARGE
        assert info[5] == WormholeTimespan.STABLE
        assert info[6] == WormholeMassspan.STABLE

    @patch('httpx.AsyncClient')
    def test_augment_map_parses_list_response(self, mock_client_cls):
        """Test parsing when API returns a list of connections directly"""
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_response = Mock()
        # Explicitly set status_code as an integer, not a Mock
        mock_response.status_code = 200
        
        mock_data = [
            {
                "source": "30000142",
                "target": "31000005",
                "type": "H121",
                "life": "critical",
                "mass": "destab",
            }
        ]
        mock_response.json.return_value = mock_data
        mock_client.get.return_value = mock_response
        
        self.pathfinder.eve_db.get_whsize_by_code.return_value = WormholeSize.SMALL

        count = self.pathfinder.augment_map(self.solar_map)

        assert count == 1
        args = self.solar_map.add_connection.call_args[0]
        info = args[3]
        assert info[1] == "H121"
        assert info[4] == WormholeSize.SMALL
        assert info[5] == WormholeTimespan.CRITICAL
        assert info[6] == WormholeMassspan.DESTAB

    @patch('httpx.AsyncClient')
    def test_augment_map_handles_errors(self, mock_client_cls):
        """Test that API errors are handled gracefully"""
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response

        count = self.pathfinder.augment_map(self.solar_map)

        assert count == -1
        self.solar_map.add_connection.assert_not_called()