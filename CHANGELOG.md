# Changelog

## [1.0.0] - 2026-01-13

### ✅ Working Implementation

This is the first complete working release of the Ruuvi Gateway Bluetooth Proxy integration for Home Assistant.

### Features

- **MQTT Integration**: Uses Home Assistant's built-in MQTT integration (no external libraries)
- **Bluetooth Scanner Registration**: Properly registers each Ruuvi Gateway as a remote Bluetooth scanner
- **Device Hierarchy**: Automatic device creation in correct domains
  - Gateway devices in `ruuvi_gateway_bt_proxy` domain
  - Scanner devices automatically created in `bluetooth` domain by HA's Bluetooth integration
- **Gateway Status Monitoring**: Real-time online/offline status via MQTT `gw_status` messages
- **Per-Gateway RSSI Filtering**: Individual RSSI thresholds for each gateway
- **Flexible Filtering**: Gateway and device whitelists
- **Intelligent Batching**: Configurable observation coalescing to reduce processing
- **Timestamp Synchronization**: Proper conversion to monotonic time
- **Diagnostics**: Full diagnostics endpoint and optional debug sensors
- **UI Configuration**: Complete config flow with validation
- **Material Design Icons**: Custom icons for all entity types

### Technical Implementation

#### Scanner Registration
- Uses `BaseHaRemoteScanner(source, adapter, connector, connectable)` from `habluetooth`
- Registers with `async_register_scanner()` passing:
  - `source_domain`: Our integration domain
  - `source_model`: "Ruuvi Gateway"
  - `source_config_entry_id`: Config entry ID
  - `source_device_id`: Gateway device ID for proper linking
- Source is gateway MAC address (e.g., `C1:05:28:BF:A7:E7`), not custom string
- Bluetooth integration automatically creates scanner device in `bluetooth` domain

#### Device Structure
```
Ruuvi Gateway Bluetooth Proxy Integration
└── Gateway Device (ruuvi_gateway_bt_proxy domain)
    ├── binary_sensor.status (online/offline)
    ├── number.rssi_filter (per-gateway threshold)
    └── Linked Device:
        └── Bluetooth Scanner (bluetooth domain)
            └── Source: <gateway_mac>
```

#### Compatibility
- ✅ Bermuda BLE Trilateration: Scanners properly recognized
- ✅ ESPHome pattern: Follows same registration pattern
- ✅ Official APIs: Uses only documented Bluetooth integration APIs

### Documentation

- `README.md`: Complete user documentation (377 lines)
- `ARCHITECTURE.md`: Technical architecture details
- `IMPLEMENTATION_SUMMARY.md`: Implementation overview
- `SCANNER_REGISTRATION.md`: Detailed scanner registration documentation
- `QUICKSTART.md`: Quick setup guide
- `DEVICE_CREATION_GUIDE.md`: Device registry guide

### Testing

- Unit tests for coordinator functionality
- Unit tests for advertisement parsing
- Unit tests for config flow
- Tests for filtering, coalescing, and timestamp handling

### Fixed Issues During Development

1. ❌ **Initial Issue**: Custom source strings like `ruuvi_gw_c10528bfa7e7`
   - ✅ **Fixed**: Use gateway MAC directly (`C1:05:28:BF:A7:E7`)

2. ❌ **Initial Issue**: Wrong domain in manifest.json (`ruuvi` instead of `ruuvi_gateway_bt_proxy`)
   - ✅ **Fixed**: Domain must match folder name

3. ❌ **Initial Issue**: Incorrect `BaseHaRemoteScanner` parameter order
   - ✅ **Fixed**: First parameter is `source`, not `hass`

4. ❌ **Initial Issue**: Manual scanner device creation in wrong domain
   - ✅ **Fixed**: Let Bluetooth integration create scanner device automatically

5. ❌ **Initial Issue**: Scanner not linked to gateway device
   - ✅ **Fixed**: Pass `source_device_id` to `async_register_scanner`

### Breaking Changes

N/A - First release

### Migration Guide

N/A - First release

### Known Limitations

- Passive scanning only (no Bluetooth connections)
- Requires Home Assistant's MQTT integration to be configured
- Requires Ruuvi Gateway firmware that supports MQTT

### Requirements

- Home Assistant 2024.1.0 or newer
- MQTT integration configured and connected
- Ruuvi Gateway with MQTT enabled

### Credits

- Integration pattern inspired by ESPHome Bluetooth implementation
- Uses Home Assistant's Bluetooth integration architecture
- Built for Bermuda BLE Trilateration compatibility

### Links

- GitHub: https://github.com/eburi/hass_ruuvi_gateway_bluetooth_proxy
- Issues: https://github.com/eburi/hass_ruuvi_gateway_bluetooth_proxy/issues
- Ruuvi Gateway: https://ruuvi.com/gateway/
- Bermuda: https://github.com/agittins/bermuda
