# Project Structure

```
hass_ruuvi_gateway_bluetooth_proxy/
├── custom_components/
│   └── ruuvi_gateway_bt_proxy/
│       ├── __init__.py                   # Integration entry point, setup/unload
│       ├── manifest.json                 # Integration metadata
│       ├── const.py                      # Constants and configuration keys
│       ├── config_flow.py                # UI configuration flow
│       ├── coordinator.py                # Main coordinator (MQTT + Bluetooth)
│       ├── advertisement_parser.py       # BLE advertisement data parser
│       ├── diagnostics.py                # Diagnostics data provider
│       ├── sensor.py                     # Optional debug sensors
│       ├── strings.json                  # UI strings
│       └── translations/
│           └── en.json                   # English translations
├── tests/
│   ├── __init__.py
│   ├── conftest.py                       # Pytest fixtures
│   ├── const.py                          # Test constants
│   ├── test_init.py                      # Tests for __init__.py
│   ├── test_config_flow.py               # Tests for config flow
│   ├── test_coordinator.py               # Tests for coordinator
│   └── test_advertisement_parser.py      # Tests for BLE parser
├── README.md                             # Full documentation
├── LICENSE                               # MIT License
├── .gitignore                            # Git ignore rules
├── pyproject.toml                        # Python project configuration
└── hacs.json                             # HACS metadata
```

## Key Features Implemented

### 1. MQTT Integration (HA Built-in Only)
- ✅ Uses `homeassistant.components.mqtt.async_subscribe`
- ✅ No external MQTT libraries (paho-mqtt, gmqtt, etc.)
- ✅ Gracefully handles MQTT not ready (ConfigEntryNotReady)

### 2. Configuration Flow
- ✅ UI-based configuration (no yaml)
- ✅ Inputs: topic prefix, QoS, whitelists, RSSI filter, batch window
- ✅ Options flow for runtime reconfiguration
- ✅ MAC address validation and normalization

### 3. MQTT Topic Handling
- ✅ Subscribes to `<prefix>+/+` pattern
- ✅ Parses topics: `ruuvi/<gateway_mac>/<ble_mac>`
- ✅ Parses JSON payloads with rssi, ts, data fields

### 4. Filtering
- ✅ Gateway MAC whitelist (optional)
- ✅ BLE device MAC whitelist (optional)
- ✅ RSSI minimum threshold
- ✅ Statistics for filtered packets

### 5. BLE Advertisement Parsing
- ✅ Parses raw AD structures from hex data
- ✅ Supports manufacturer data (0xFF)
- ✅ Supports service data (0x16, 0x21)
- ✅ Supports service UUIDs (0x02/0x03/0x06/0x07)
- ✅ Extracts local name, TX power
- ✅ Graceful fallback on parsing errors

### 6. Bluetooth Backend Integration
- ✅ Registers external scanner per gateway
- ✅ Uses `bluetooth.async_register_scanner`
- ✅ Uses `bluetooth.async_get_advertisement_callback`
- ✅ Creates proper `BluetoothServiceInfoBleak` objects
- ✅ Stable source naming: Gateway MAC address (e.g., `C1:05:28:BF:A7:E7`)

### 7. Batching & Rate Limiting
- ✅ Buffer per gateway
- ✅ Coalesces by BLE device within batch window
- ✅ Keeps most recent or highest RSSI
- ✅ Configurable batch window (50-5000ms)
- ✅ Periodic flush task

### 8. Diagnostics & Monitoring
- ✅ Diagnostics endpoint with full stats
- ✅ Optional debug sensors when enabled:
  - Packets Received
  - Packets Forwarded
  - Packets Dropped
  - Active Gateways (with MAC list)
- ✅ Detailed error counters (invalid JSON, topic, hex, etc.)

### 9. Cleanup & Lifecycle
- ✅ Proper unsubscribe on unload
- ✅ Cancel flush tasks cleanly
- ✅ Clean entry unload and reload
- ✅ No lingering tasks or subscriptions

### 10. Testing
- ✅ Unit tests for topic parsing
- ✅ Unit tests for payload parsing
- ✅ Unit tests for AD structure parsing
- ✅ Unit tests for filtering logic
- ✅ Unit tests for coalescing
- ✅ Config flow tests

### 11. Documentation
- ✅ Comprehensive README.md
- ✅ Explicitly states "uses HA's built-in MQTT integration"
- ✅ Setup prerequisites
- ✅ Example topics/payloads
- ✅ Troubleshooting guide
- ✅ Debug logging instructions

## Architecture Overview

```
┌─────────────────┐
│ Ruuvi Gateway   │ publishes MQTT topics
└────────┬────────┘
         │ ruuvi/<gw_mac>/<ble_mac>
         ▼
┌─────────────────────────────┐
│ HA MQTT Integration         │
│ (Built-in, user configured) │
└────────────┬────────────────┘
             │ async_subscribe
             ▼
┌──────────────────────────────┐
│ RuuviGatewayCoordinator      │
│ - Parse topic & payload      │
│ - Apply filters              │
│ - Buffer & coalesce          │
│ - Parse BLE AD structures    │
└────────────┬─────────────────┘
             │ BluetoothServiceInfoBleak
             ▼
┌──────────────────────────────┐
│ HA Bluetooth Integration     │
│ - Registered scanners        │
│ - Advertisement callback     │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│ Other Integrations           │
│ (Bermuda, device trackers,   │
│  etc.)                       │
└──────────────────────────────┘
```

## Implementation Highlights

### No External Dependencies
- manifest.json lists only `mqtt` and `bluetooth` (both built-in)
- No requirements in manifest.json
- Uses only standard library + Home Assistant APIs

### Async-Safe MQTT Handler
- Callback is @callback decorated
- Fast parsing and buffering
- No blocking operations
- Deferred processing in flush task

### Robust Error Handling
- Invalid JSON → increment counter, continue
- Invalid hex → increment counter, continue
- Invalid topic → increment counter, continue
- Parsing failures → forward minimal advertisement

### Per-Gateway Scanner Registration
- Each gateway gets unique source ID
- Allows proper attribution in Bluetooth backend
- Enables multi-gateway scenarios

### Configurable Batching
- Default 250ms window
- Reduces processing overhead
- Preserves best signal (highest RSSI)
- Per-gateway buffering

## Usage Example

1. **Configure MQTT Integration** (one-time)
   - Settings → Devices & Services → Add Integration → MQTT
   - Enter broker details

2. **Add Ruuvi Gateway BT Proxy**
   - Settings → Devices & Services → Add Integration
   - Search "Ruuvi Gateway"
   - Configure:
     - Topic Prefix: `ruuvi/`
     - Enable Debug Entity: ✓

3. **Monitor in HA**
   - Diagnostics show active gateways
   - Debug sensors show packet counts
   - Bluetooth integration sees devices

4. **Use with Bermuda** (optional)
   - Install Bermuda
   - Configure for presence detection
   - Bermuda automatically uses Ruuvi Gateway scanners
