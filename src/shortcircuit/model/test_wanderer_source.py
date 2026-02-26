from unittest.mock import MagicMock

import pytest

from shortcircuit.model.wanderer_source import WandererSource


def test_wanderer_source_fetch_data():
  """Test that Wanderer source fetches data correctly."""
  # Create a mock Wanderer instance
  mock_wanderer = MagicMock()
  mock_wanderer.augment_map.return_value = 5  # Simulate 5 connections

  # Create a WandererSource instance with the mock Wanderer
  wanderer_source = WandererSource(
    name="Test Wanderer",
    url="http://example.com",
    map_id="123",
    token="test_token",
  )
  wanderer_source._wanderer = mock_wanderer

  # Call fetch_data
  connections_added = wanderer_source.fetch_test_data()

  # Assertions
  assert connections_added == 5
  mock_wanderer.augment_map.assert_called_once()


# Example Usage (replace with your actual test):
# pytest src/shortcircuit/model/test_wanderer_source.py