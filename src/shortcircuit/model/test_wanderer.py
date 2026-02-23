# src/shortcircuit/model/test_wanderer.py

import json
from unittest.mock import Mock, patch
import pytest
from shortcircuit.model.wanderer import Wanderer
from shortcircuit.model.solarmap import SolarMap, ConnectionType
from shortcircuit.model.evedb import EveDb, WormholeSize, WormholeTimespan, WormholeMassspan

class TestWanderer:
    def setup_method(self):
        self.wanderer = Wanderer("http://test.url", "map123", "token123")
        # Mock EveDb to avoid loading CSVs
        self.wanderer.eve_db = Mock(spec=EveDb)
        self.wanderer.eve_db.get_whsize_by_code.return_value = WormholeSize.UNKNOWN
        self.wanderer.eve_db.get_whsize_by_system.return_value = WormholeSize.UNKNOWN
        
        self.solar_map = Mock(spec=SolarMap)

    @patch('httpx.t = mock_client_cls.return_value.__aenter__.return_value
        mock_response.status_code = 200
        
        # Sample data based on user input
        mock_data = {
            "data": [
                {
                    "id": "uuid-1",
                    "name": "Unknown",
                    "type": "K162",
                    "group": "Wormhole",
                    "kind": "Cosmic Signature",
                    "eve_id": "ABC-123",
                    "solar_system_id": 30000142, # Jita
                    "linked_system_id": 31000005, # Thera
                    "custom_info": '{"time_status": 1, "mass_status": 1}',
                    "updated_at": "2026-02-23T18:05:02Z"
                },
                {
                    "id": "uuid-2",
                    "group": "Combat Site", # Should be ignored
                    "solar_system_id": 30000142,
                    "linked_system_id": 31000005
                }
            ]
        }
        mock_response.json.return_value = mock_data
        mock_client.get.return_value = mock_response

        # Seoeanderer.eve_db.get_whsize_by_code.return_value = WormholeSize.LARGE

        # Ex= self.wanderer.augment_map(self.solar_map)

        # Verify
        assert count == 1
        self.solar_map.add_connection.assert_called_once()
        
        args = self.solar_map.add_connection.call_args[0]
        assert args[0] == 30000142
        assert args[1] == 31000005
        assert args[2] == ConnectionType.WORMHOLE
        
        info = args[3]
        # [sig_id, wh_type, out_sig, out_type, size, life, mass, elapsed]
        assert info[0] == "ABC-123"
        assert info[1] == "K162"
        assert info[2] == "???" # Out signature unknown
        assert info[3] == "????" # Out type unknown because in is K162
        assert info[4] == WormholeSize.LARGE
        assert info[5] == WormholeTimespan.STABLE
        assert info[6] == WormholeMassspan.STABLE
        assert isinstance(info[7], float)
        assert info[8] == "Wanderer"

    @patch('httpx.AsyncClient')
    def test_augment_map_eol_crit(self, mock_client_cls):
        mock_response = Mock()
        mock_clien
        mock_data = {
            "data": [
                {  "type": "H121",
                    "solar_system_id": 30000142,
                    "linked_system_id": 31000005,
                    "custom_info": '{"time_status": 2, "mass_status": 3}', # EOL, Crit
                    "updated_at": "2026-02-23T18:05:02Z"
                }
            ]
        }
        mock_response.json.return_value = mock_data
        mock_client.get.return_value = mock_response
        
        self.wanderer.eve_db.get_whsize_by_code.return_value = WormholeSize.SMALL

        count = self.wanderer.augment_map(self.solar_map)
         count == 1
        args = self.solar_map.add_connection.call_args[0]
        info = args[3]
        
        assert info[1] == "H121"
        asser  info[5] == WormholeTimespan.CRITICAL
        assert info[6] == WormholeMassspan.CRITICAL

    @patch('httpx.AsyncClient')
    def test_augment_map_api_failure(self, mock_client_cls):
        mock_response = Mock()
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_response.status_code = 500        mock_client.get.return_value = mock_response
map)
        assert count == -1
        self.solar_map.add_connection.assert_not_called()