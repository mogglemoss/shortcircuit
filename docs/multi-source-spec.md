# Multi-Source Configuration Specification

## Objective
Enable Short Circuit to support multiple instances of map providers (e.g., multiple Tripwire accounts, distinct Wanderer maps) simultaneously. This allows users to aggregate data from various sources (Corp, Alliance, Public) into a single solar map.

## Current Limitations
- **Singleton Configuration**: The app currently stores a single set of credentials for Tripwire, Wanderer, etc., in flat `QSettings`.
- **Static Logic**: The `Tripwire` class and `SolarMap` logic assume a single data stream.
- **Data Collisions**: `SolarMap.add_neighbor` currently ignores updates if a connection already exists, preventing newer data from overwriting older data.

## Proposed Architecture

### 1. Backend: Source Management
**`MapSource` (Abstract Base Class)**
- Defines the interface for all providers.
- **Methods**: `fetch_data()`, `connect()`, `get_status()`, `to_json()`, `from_json()`.
- **Properties**: `id` (UUID), `type` (enum: TRIPWIRE, WANDERER, PATHFINDER), `name` (user-defined), `enabled` (bool).

**`SourceManager`**
- Singleton class responsible for the lifecycle of `MapSource` instances.
- **Responsibilities**:
    - Load configuration from `QSettings`.
    - Instantiate specific implementations (`TripwireSource`, `WandererSource`) based on config.
    - Aggregate data fetching: Iterate through enabled sources to update the `SolarMap`.
    - Handle background threading for updates.

### 2. Data Model & Storage
Transition from flat `QSettings` keys (e.g., `Tripwire/url`) to a JSON-serialized list stored in a single key (e.g., `MapSources`).

**JSON Schema:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "tripwire",
    "name": "Corp Tripwire",
    "enabled": true,
    "config": {
      "url": "https://tripwire.eve-apps.com",
      "username": "user",
      "password": "encrypted_or_stored_securely"
    }
  },
  {
    "id": "770e8400-e29b-41d4-a716-446655441111",
    "type": "wanderer",
    "name": "Alliance Map",
    "enabled": false,
    "config": {
      "url": "...",
      "map_id": "...",
      "token": "..."
    }
  }
]
```

### 3. Data Merging Logic
**`SolarMap.add_neighbor` Refactor**
- **Current Behavior**: If connection exists, return (ignore new data).
- **New Behavior**: If connection exists, compare `modifiedTime` (or `time_elapsed`).
    - If new data is **newer**, overwrite the connection.
    - If new data is **older**, ignore it.
    - *Edge Case*: If timestamps are identical, prioritize "Stable" status over "Critical".

### 4. User Interface
**Settings Dialog Overhaul**
- **Master-Detail View**:
    - **Left Pane**: List of configured sources with "Add" (+) and "Remove" (-) buttons.
    - **Right Pane**: Configuration form specific to the selected source type.

**Main Window**
- **Source Toggles**: A new widget (sidebar or status bar menu) to quickly toggle specific sources on/off without opening settings.

## Migration Strategy
1.  **Startup Check**: `SourceManager` checks for legacy `QSettings` keys (e.g., `Tripwire/url`).
2.  **Convert**: If found, create a new `MapSource` entry in the new list format using the old values.
3.  **Cleanup**: Remove legacy keys to prevent re-migration.