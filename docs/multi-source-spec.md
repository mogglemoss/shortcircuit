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

## Future Opportunities (Phase 2)

### 1. Modularization of `app.py`
*   **Problem:** `app.py` currently acts as a "God Object", handling UI layout, business logic, and thread management.
*   **Solution:** Extract UI layout into `view/main_window_ui.py` and move logic into a Controller layer.

### 2. Strengthening Type Safety
*   **Problem:** Reliance on positional lists for complex data is brittle.
*   **Solution:** Standardize on the `ConnectionData` dataclass and implement strict `TypedDict` for pathfinding restrictions.

### 3. Network Resilience and Observability
*   **Problem:** Transient network failures mark sources as "Error" without retry.
*   **Solution:** Implement exponential backoff retries and add a "Source Log" console in the UI.

### 4. Graph Update Efficiency
*   **Problem:** Full graph rebuild on every source update.
*   **Solution:** Implement incremental graph updates to only modify affected edges.

### 5. Asynchronous UI Patterns
*   **Problem:** Large data merges can cause UI stutters.
*   **Solution:** Explore `qasync` for native `asyncio` integration with the Qt event loop.

### 6. Style and Naming Consistency
*   **Solution:** Systematic refactor to `snake_case` for all methods and variables to comply with PEP 8.