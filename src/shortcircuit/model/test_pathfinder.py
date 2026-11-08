"""Tests for the Pathfinder mapper integration

Covers config validation, endpoint derivation, the connection translation
(life/mass keywords, size fallbacks), and the failure modes of the API
round trip.
"""

import unittest
from unittest import mock

import requests

from shortcircuit.model import pathfinder as pathfinder_module
from shortcircuit.model.evedb import WormholeMassspan, WormholeSize, WormholeTimespan
from shortcircuit.model.pathfinder import Pathfinder
from shortcircuit.model.solarmap import ConnectionType

THERA_ID = 31000005
J_SYSTEM_ID = 31002238


def _make_pathfinder(**kwargs):
  defaults = dict(
    url='https://pathfinder.example.com',
    token='secret-token',
    name='Test Pathfinder',
  )
  defaults.update(kwargs)
  p = Pathfinder(**defaults)
  p.eve_db = mock.Mock()
  p.eve_db.get_whsize_by_code.return_value = WormholeSize.UNKNOWN
  p.eve_db.get_whsize_by_system.return_value = WormholeSize.LARGE
  return p


def _response(status_code=200, payload=None):
  r = mock.Mock()
  r.status_code = status_code
  r.json = mock.Mock(return_value=payload if payload is not None else {'connections': []})
  return r


def _connection(**overrides):
  conn = {
    'source': J_SYSTEM_ID,
    'target': THERA_ID,
    'source_sig': 'ABC-123',
    'target_sig': 'XYZ-789',
    'type': 'F353',
    'life': 'stable',
    'mass': 'stable',
    'updated_at': '2026-11-08T00:00:00Z',
  }
  conn.update(overrides)
  return conn


class TestPathfinderConfig(unittest.TestCase):

  def test_valid_config(self):
    self.assertEqual(_make_pathfinder().validate_config(), (True, None))

  def test_token_is_optional(self):
    self.assertEqual(_make_pathfinder(token='').validate_config(), (True, None))

  def test_missing_url_is_reported(self):
    is_valid, error = _make_pathfinder(url='').validate_config()
    self.assertFalse(is_valid)
    self.assertEqual(error, 'URL is required')

  def test_url_normalization(self):
    p = _make_pathfinder(url='pathfinder.example.com/')
    self.assertEqual(p.url, 'https://pathfinder.example.com')


class TestPathfinderAugmentMap(unittest.TestCase):

  def _augment(self, connections, pathfinder=None, payload=None):
    p = pathfinder or _make_pathfinder()
    solar_map = mock.Mock()
    if payload is None:
      payload = {'connections': connections}
    with mock.patch.object(
      pathfinder_module.requests, 'get',
      return_value=_response(payload=payload),
    ) as fake_get:
      count = p.augment_map(solar_map)
    return count, solar_map, fake_get

  def test_connection_is_translated(self):
    count, solar_map, fake_get = self._augment([_connection()])

    self.assertEqual(count, 1)
    url = fake_get.call_args.kwargs['url']
    self.assertEqual(url, 'https://pathfinder.example.com/api/connections')
    headers = fake_get.call_args.kwargs['headers']
    self.assertEqual(headers['Authorization'], 'Bearer secret-token')

    args, kwargs = solar_map.add_connection.call_args
    source, dest, con_type, info = args
    self.assertEqual((source, dest), (J_SYSTEM_ID, THERA_ID))
    self.assertEqual(con_type, ConnectionType.WORMHOLE)
    self.assertEqual(info[0:4], ['ABC-123', 'F353', 'XYZ-789', 'K162'])
    self.assertEqual(kwargs['source_name'], 'Test Pathfinder')

  def test_explicit_json_url_is_used_verbatim(self):
    p = _make_pathfinder(url='https://pathfinder.example.com/export.json')
    _, _, fake_get = self._augment([], pathfinder=p)
    self.assertEqual(
      fake_get.call_args.kwargs['url'],
      'https://pathfinder.example.com/export.json',
    )

  def test_no_auth_header_without_token(self):
    p = _make_pathfinder(token='')
    _, _, fake_get = self._augment([], pathfinder=p)
    self.assertNotIn('Authorization', fake_get.call_args.kwargs['headers'])

  def test_bare_list_payload_is_accepted(self):
    count, _, _ = self._augment(None, payload=[_connection()])
    self.assertEqual(count, 1)

  def test_life_and_mass_keywords(self):
    count, solar_map, _ = self._augment([
      _connection(life='critical', mass='destabilized'),
    ])
    self.assertEqual(count, 1)
    info = solar_map.add_connection.call_args.args[3]
    self.assertEqual(info[5], WormholeTimespan.CRITICAL)
    self.assertEqual(info[6], WormholeMassspan.DESTAB)

  def test_size_keyword_fallback(self):
    count, solar_map, _ = self._augment([_connection(size='XL')])
    self.assertEqual(count, 1)
    info = solar_map.add_connection.call_args.args[3]
    self.assertEqual(info[4], WormholeSize.XLARGE)

  def test_size_falls_back_to_system_pair(self):
    count, solar_map, _ = self._augment([_connection()])
    info = solar_map.add_connection.call_args.args[3]
    self.assertEqual(info[4], WormholeSize.LARGE)

  def test_incomplete_connections_are_skipped(self):
    count, solar_map, _ = self._augment([
      _connection(source=0),
      _connection(target=None),
      _connection(source='not-a-number'),
    ])
    self.assertEqual(count, 0)
    solar_map.add_connection.assert_not_called()


class TestPathfinderFailureModes(unittest.TestCase):

  def _augment_with(self, response=None, side_effect=None):
    p = _make_pathfinder()
    solar_map = mock.Mock()
    with mock.patch.object(
      pathfinder_module.requests, 'get',
      return_value=response, side_effect=side_effect,
    ):
      return p.augment_map(solar_map)

  def test_http_error_returns_error(self):
    self.assertEqual(self._augment_with(_response(status_code=500)), -1)

  def test_network_exception_returns_error(self):
    self.assertEqual(
      self._augment_with(side_effect=requests.ConnectionError('offline')), -1
    )

  def test_unexpected_shape_returns_error(self):
    self.assertEqual(
      self._augment_with(_response(payload={'connections': 'nope'})), -1
    )

  def test_misconfigured_returns_error_without_network(self):
    p = _make_pathfinder(url='')
    solar_map = mock.Mock()
    with mock.patch.object(pathfinder_module.requests, 'get') as fake_get:
      self.assertEqual(p.augment_map(solar_map), -1)
    fake_get.assert_not_called()


if __name__ == '__main__':
  unittest.main()
