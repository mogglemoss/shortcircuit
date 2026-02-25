from datetime import datetime, timedelta
from shortcircuit.model.connection_db import ConnectionDB, ConnectionData
from shortcircuit.model.solarmap import ConnectionType
from shortcircuit.model.evedb import WormholeSize, WormholeTimespan, WormholeMassspan

def test_freshness_wins():
    db = ConnectionDB()
    
    conn1 = ConnectionData(
        source_id="source1",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=2.0  # 2 hours old
    )
    
    conn2 = ConnectionData(
        source_id="source2",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=1.0  # 1 hour old (Fresher)
    )
    
    db.add_connection(conn1)
    db.add_connection(conn2)
    
    resolved = db.get_resolved_connections()
    assert len(resolved) == 1
    assert resolved[0].source_id == "source2"


def test_health_wins_tiebreaker():
    db = ConnectionDB()
    
    conn1 = ConnectionData(
        source_id="source1",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=1.0,
        wh_life=WormholeTimespan.CRITICAL
    )
    
    conn2 = ConnectionData(
        source_id="source2",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=1.0,
        wh_life=WormholeTimespan.STABLE  # Healthier
    )
    
    db.add_connection(conn1)
    db.add_connection(conn2)
    
    resolved = db.get_resolved_connections()
    assert len(resolved) == 1
    assert resolved[0].source_id == "source2"


def test_gate_wins_over_wormhole():
    db = ConnectionDB()
    
    conn1 = ConnectionData(
        source_id="source1",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=0.1
    )
    
    conn2 = ConnectionData(
        source_id="source2",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.GATE,
        time_elapsed=10.0
    )
    
    db.add_connection(conn1)
    db.add_connection(conn2)
    
    resolved = db.get_resolved_connections()
    assert len(resolved) == 1
    assert resolved[0].source_id == "source2"


def test_stale_data_ignored():
    db = ConnectionDB()
    
    conn1 = ConnectionData(
        source_id="source1",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=50.0  # Stale, max is 48
    )
    
    db.add_connection(conn1)
    
    resolved = db.get_resolved_connections(max_age_hours=48.0)
    assert len(resolved) == 0


def test_independent_paths():
    db = ConnectionDB()
    
    conn1 = ConnectionData(
        source_id="source1",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=1.0
    )
    
    conn2 = ConnectionData(
        source_id="source2",
        source_system=2,
        dest_system=3,
        con_type=ConnectionType.WORMHOLE,
        time_elapsed=1.0
    )
    
    db.add_connection(conn1)
    db.add_connection(conn2)
    
    resolved = db.get_resolved_connections()
    assert len(resolved) == 2


def test_clear_source():
    db = ConnectionDB()
    
    conn1 = ConnectionData(
        source_id="source1",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
    )
    
    conn2 = ConnectionData(
        source_id="source2",
        source_system=1,
        dest_system=2,
        con_type=ConnectionType.WORMHOLE,
    )
    
    db.add_connection(conn1)
    db.add_connection(conn2)
    
    db.clear_source("source1")
    
    resolved = db.get_resolved_connections()
    assert len(resolved) == 1
    assert resolved[0].source_id == "source2"
