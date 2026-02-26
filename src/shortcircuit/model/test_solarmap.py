from shortcircuit.model.evedb import EveDb, SpaceType, WormholeSize, WormholeMassspan, WormholeTimespan
from shortcircuit.model.solarmap import ConnectionType, SolarMap
from shortcircuit.model.connection_db import ConnectionData

# FIXME(secondfry): why is `shortest_path` unstable?
# All tests here should have Jita as destination, not Ikuchi.


def test_dodixie_jita():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Ikuchi"),
    {
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      }
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ourapheh',
    'Chantrousse',
    'Tierijev',
    'Tannolen',
    'Onatoh',
    'Sujarento',
    'Tama',
    'Nourvukaiken',
    'Tunttaras',
    'Ikuchi',
  ]


def test_dodixie_jita_but_avoid_tama():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Ikuchi"),
    {
      "avoidance_list": [
        eve_db.name2id("Tama"),
      ],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      }
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ourapheh',
    'Manarq',
    'Tar',
    'Tekaima',
    'Tarta',
    'Vecamia',
    'Cleyd',
    'Lor',
    'Ahbazon',
    'Hykkota',
    'Ansila',
    'Ikuchi',
  ]


def test_dodixie_jita_but_avoid_hs():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Sujarento"),
    {
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 100,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      }
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Erme',
    'Villore',
    'Old Man Star',
    'Heydieles',
    'Fliet',
    'Deven',
    'Nagamanen',
    'Sujarento',
  ]


def test_wh_botane_ikuchi():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Botane"),
      dest_system=eve_db.name2id("Ikuchi"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.SMALL,
      wh_life=WormholeTimespan.CRITICAL,
      wh_mass=WormholeMassspan.CRITICAL,
      time_elapsed=42.21
    )
  )
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Jita"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": False,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ikuchi',
    'Jita',
  ]


def test_wh_botane_ikuchi_but_medium():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Botane"),
      dest_system=eve_db.name2id("Ikuchi"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      code_source="Q063",
      sig_dest="DEF-456",
      code_dest="K162",
      wh_size=WormholeSize.SMALL,
      wh_life=WormholeTimespan.CRITICAL,
      wh_mass=WormholeMassspan.CRITICAL,
      time_elapsed=42.21
    )
  )
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Ikuchi"),
    {
      "size_restriction": {
        WormholeSize.SMALL: True,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": False,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ourapheh',
    'Chantrousse',
    'Tierijev',
    'Tannolen',
    'Onatoh',
    'Sujarento',
    'Tama',
    'Nourvukaiken',
    'Tunttaras',
    'Ikuchi',
  ]


def test_wh_botane_ikuchi_but_not_eol():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Botane"),
      dest_system=eve_db.name2id("Ikuchi"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.SMALL,
      wh_life=WormholeTimespan.CRITICAL,
      wh_mass=WormholeMassspan.CRITICAL,
      time_elapsed=42.21
    )
  )
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Ikuchi"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": True,
      "ignore_masscrit": False,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ourapheh',
    'Chantrousse',
    'Tierijev',
    'Tannolen',
    'Onatoh',
    'Sujarento',
    'Tama',
    'Nourvukaiken',
    'Tunttaras',
    'Ikuchi',
  ]


def test_wh_botane_ikuchi_but_not_crit():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Botane"),
      dest_system=eve_db.name2id("Ikuchi"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.SMALL,
      wh_life=WormholeTimespan.CRITICAL,
      wh_mass=WormholeMassspan.CRITICAL,
      time_elapsed=42.21
    )
  )
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Ikuchi"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": True,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ourapheh',
    'Chantrousse',
    'Tierijev',
    'Tannolen',
    'Onatoh',
    'Sujarento',
    'Tama',
    'Nourvukaiken',
    'Tunttaras',
    'Ikuchi',
  ]


def test_wh_botane_ikuchi_but_not_stale():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Botane"),
      dest_system=eve_db.name2id("Ikuchi"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.SMALL,
      wh_life=WormholeTimespan.CRITICAL,
      wh_mass=WormholeMassspan.CRITICAL,
      time_elapsed=42.21
    )
  )
  path = map.shortest_path(
    eve_db.name2id("Dodixie"),
    eve_db.name2id("Ikuchi"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": False,
      "age_threshold": 16,
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Dodixie',
    'Botane',
    'Ourapheh',
    'Chantrousse',
    'Tierijev',
    'Tannolen',
    'Onatoh',
    'Sujarento',
    'Tama',
    'Nourvukaiken',
    'Tunttaras',
    'Ikuchi',
  ]


def test_jita_tama_but_avoid_tama():
  eve_db = EveDb()
  map = SolarMap(eve_db)
  path = map.shortest_path(
    eve_db.name2id("Ikuchi"),
    eve_db.name2id("Tama"),
    {
      "avoidance_list": [
        eve_db.name2id("Tama"),
      ],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  assert named_path == [
    'Ikuchi',
    'Tunttaras',
    'Nourvukaiken',
    'Tama',
  ]


def test_zarzakh_avoided_as_transit():
  """
  Test that Zarzakh is automatically excluded from routes where it would be
  an intermediate waypoint. Zarzakh has emanation locks that prevent transit.
  See: https://github.com/secondfry/shortcircuit/issues/30
  """
  eve_db = EveDb()
  map = SolarMap(eve_db)
  
  # Create wormhole connections that would make Zarzakh an attractive transit point
  # Jita -> G-0Q86 (wormhole) -> Zarzakh (gate) -> H-PA29 (gate) -> Dodixie (wormhole)
  # Without the Zarzakh exclusion, this would be the shortest path
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Jita"),
      dest_system=eve_db.name2id("G-0Q86"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.LARGE,
      wh_life=WormholeTimespan.STABLE,
      wh_mass=WormholeMassspan.STABLE,
      time_elapsed=1.0
    )
  )
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("H-PA29"),
      dest_system=eve_db.name2id("Dodixie"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="GHI-789",
      sig_dest="JKL-012",
      wh_size=WormholeSize.LARGE,
      wh_life=WormholeTimespan.STABLE,
      wh_mass=WormholeMassspan.STABLE,
      time_elapsed=1.0
    )
  )
  
  path = map.shortest_path(
    eve_db.name2id("Jita"),
    eve_db.name2id("Dodixie"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": False,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  # Verify Zarzakh is not in the path as an intermediate system
  assert "Zarzakh" not in named_path


def test_zarzakh_as_destination():
  """
  Test that Zarzakh can be used as a destination system.
  Even though it's excluded from transit, players should be able to route TO it.
  See: https://github.com/secondfry/shortcircuit/issues/30
  """
  eve_db = EveDb()
  map = SolarMap(eve_db)
  
  # Add wormhole connection from Ikuchi to G-0Q86
  # This creates a fast path: Ikuchi -> G-0Q86 -> Zarzakh
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Ikuchi"),
      dest_system=eve_db.name2id("G-0Q86"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.LARGE,
      wh_life=WormholeTimespan.STABLE,
      wh_mass=WormholeMassspan.STABLE,
      time_elapsed=1.0
    )
  )
  
  # Route from Ikuchi to Zarzakh
  path = map.shortest_path(
    eve_db.name2id("Ikuchi"),
    eve_db.name2id("Zarzakh"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": False,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  # Verify the exact path: Ikuchi -> G-0Q86 -> Zarzakh
  assert named_path == ["Ikuchi", "G-0Q86", "Zarzakh"]


def test_zarzakh_as_source():
  """
  Test that Zarzakh can be used as a source system.
  Even though it's excluded from transit, players should be able to route FROM it.
  See: https://github.com/secondfry/shortcircuit/issues/30
  """
  eve_db = EveDb()
  map = SolarMap(eve_db)
  
  # Add wormhole connection from Turnur to Perimeter
  # This creates a fast path: Zarzakh -> Turnur -> Perimeter
  map.add_connection(
    ConnectionData(
      source_id="test",
      source_system=eve_db.name2id("Turnur"),
      dest_system=eve_db.name2id("Perimeter"),
      con_type=ConnectionType.WORMHOLE,
      sig_source="ABC-123",
      sig_dest="DEF-456",
      wh_size=WormholeSize.LARGE,
      wh_life=WormholeTimespan.STABLE,
      wh_mass=WormholeMassspan.STABLE,
      time_elapsed=1.0
    )
  )
  
  # Route from Zarzakh to Perimeter
  path = map.shortest_path(
    eve_db.name2id("Zarzakh"),
    eve_db.name2id("Perimeter"),
    {
      "size_restriction": {
        WormholeSize.SMALL: False,
        WormholeSize.MEDIUM: False,
        WormholeSize.LARGE: False,
        WormholeSize.XLARGE: False,
      },
      "avoidance_list": [],
      "security_prio": {
        SpaceType.HS: 1,
        SpaceType.LS: 1,
        SpaceType.NS: 1,
        SpaceType.WH: 1,
      },
      "ignore_eol": False,
      "ignore_masscrit": False,
      "age_threshold": float('inf'),
    },
  )

  named_path = [eve_db.id2name(x) for x in path]
  # Verify the exact path: Zarzakh -> Turnur -> Perimeter
  assert named_path == ["Zarzakh", "Turnur", "Perimeter"]
