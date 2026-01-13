# Ruuvi Gateway Bluetooth Proxy

A Home Assistant custom integration that subscribes to MQTT topics published by Ruuvi Gateways and forwards BLE advertisements to Home Assistant's Bluetooth backend.

## ⚠️ Important: MQTT Integration Dependency

**This integration uses Home Assistant's built-in MQTT integration. It does not connect to MQTT directly.**

You must have the MQTT integration configured and connected in Home Assistant before using this integration.

## Features

- 🔌 **Uses HA's Built-in MQTT** - No external MQTT libraries, relies on Home Assistant's existing MQTT connection
- 📡 **Bluetooth Scanner Registration** - Properly registers each Ruuvi Gateway as a remote Bluetooth scanner with HA's Bluetooth manager
- 🏠 **Device Hierarchy** - Creates organized device structure: Gateway devices with child Bluetooth Proxy devices
- 📶 **Gateway Status Monitoring** - Real-time online/offline status via MQTT gw_status messages
- 🎯 **Flexible Filtering** - Whitelist gateways and devices, per-gateway RSSI filtering
- 📦 **Intelligent Batching** - Coalesces observations within a configurable window to reduce processing
- 🔄 **Timestamp Synchronization** - Converts gateway timestamps to monotonic time for accurate tracking
- 📊 **Diagnostics & Debug Sensors** - Optional sensors for monitoring packet statistics
- 🔧 **Full Config Flow** - Easy setup and configuration through the UI
- 🎨 **Material Design Icons** - Custom icons for all entity types

## How It Works

1. **Ruuvi Gateway** publishes BLE advertisements to MQTT topics in format: `ruuvi/<gateway_mac>/<ble_device_mac>`
2. **This Integration** subscribes to those topics using HA's MQTT integration
3. **Device Creation** - Automatically creates Gateway and Bluetooth Proxy devices for each discovered gateway
4. **Scanner Registration** - Registers each gateway as a remote Bluetooth scanner with HA's Bluetooth manager
5. **Status Monitoring** - Subscribes to `ruuvi/<gateway_mac>/gw_status` for real-time online/offline tracking
6. **Parses & Forwards** - Parses BLE advertisement data and forwards it to HA's Bluetooth backend with proper timestamps
7. **Integration Ready** - Bluetooth-based integrations (like Bermuda BLE Trilateration) automatically detect and use the scanners

## Prerequisites

### 1. MQTT Integration Setup

Configure the MQTT integration in Home Assistant:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **MQTT**
4. Configure your MQTT broker connection

### 2. Ruuvi Gateway Configuration

Configure your Ruuvi Gateway to publish to MQTT:

1. Access your Ruuvi Gateway configuration interface
2. Set up MQTT connection to your broker
3. Enable BLE advertisement publishing
4. Note the topic prefix (default is `ruuvi/`)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add `https://github.com/eburi/hass_ruuvi_gateway_bluetooth_proxy` as an Integration
5. Search for "Ruuvi Gateway Bluetooth Proxy"
6. Click Install
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ruuvi_gateway_bt_proxy` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Ruuvi Gateway Bluetooth Proxy**
4. Configure the integration:

#### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| **MQTT Topic Prefix** | `ruuvi/` | The prefix for MQTT topics (will be normalized to end with `/`) |
| **MQTT QoS** | `0` | Quality of Service level (0, 1, or 2) |
| **Gateway Whitelist** | (empty) | Comma-separated MAC addresses of gateways to accept (empty = all) |
| **Device Whitelist** | (empty) | Comma-separated BLE device MAC addresses to accept (empty = all) |
| **Batch Window (ms)** | `250` | Time window for coalescing observations (50-5000ms) |
| **Enable Debug Entity** | `false` | Enable debug sensors for monitoring statistics |

### Devices and Entities

The integration automatically creates the following devices and entities:

#### Integration Device
- **Purpose**: Houses integration-level statistics and debug information
- **Entities** (only if debug entities enabled):
  - `sensor.packets_received` - Total packets received from MQTT
  - `sensor.packets_forwarded` - Packets successfully forwarded to Bluetooth backend
  - `sensor.packets_dropped` - Packets filtered or dropped
  - `sensor.active_gateways` - Number of active gateways (with MAC addresses in attributes)

#### Per-Gateway Devices (created automatically for each discovered gateway)

1. **Gateway Device** - Represents the physical Ruuvi Gateway
   - **Entities**:
     - `binary_sensor.<gateway>_status` - Gateway online/offline status (from MQTT gw_status)
     - `number.<gateway>_rssi_filter` - Per-gateway RSSI filter threshold

2. **Bluetooth Proxy Device** - Child device linked to gateway
   - **Purpose**: Registered as a Bluetooth scanner source in HA's Bluetooth manager
   - **Visible to**: Bermuda and other Bluetooth-based integrations
   - **Scanner Source**: Gateway MAC address (e.g., `C1:05:28:BF:A7:E7`)
   - **Note**: Assign an **Area** to this device for Bermuda to use it for location tracking

### Per-Gateway RSSI Filtering

Each Ruuvi Gateway device has an **RSSI Filter** number entity that allows you to set the minimum RSSI threshold for that specific gateway. Advertisements with RSSI below this threshold will be filtered out.

- **Default**: `-127` (no filtering)
- **Range**: `-127` to `0` dBm
- **Step**: `1` dBm
- **Location**: Settings → Devices & Services → Ruuvi Gateway Bluetooth Proxy → [Gateway Device] → Controls → RSSI Filter

This allows you to optimize filtering per gateway based on location and environment. For example, you might set a higher threshold (e.g., `-70`) for a gateway in a central location to only capture nearby devices, while leaving a remote gateway at the default to capture all devices.

### Example Configuration

**Basic setup:**
- Topic Prefix: `ruuvi/`
- All other options at defaults
- Per-gateway RSSI filters at default `-127` (no filtering)

**Filtered setup for presence detection:**
- Topic Prefix: `ruuvi/`
- Gateway Whitelist: `C1:05:28:BF:A7:E7, AA:BB:CC:DD:EE:FF`
- Device Whitelist: (empty - track all devices)
- Batch Window: `500`
- Enable Debug Entity: `✓`
- Per-gateway RSSI filters:
  - Central gateway: `-60` (only nearby devices)
  - Remote gateways: `-80` (wider range)
- **Important**: Assign Areas to Bluetooth Proxy devices for Bermuda location tracking

## MQTT Topic Format

The integration subscribes to topics matching:

```
<prefix>+/+           # BLE advertisements
<prefix>+/gw_status   # Gateway status messages
```

Default: `ruuvi/+/+` and `ruuvi/+/gw_status`

### BLE Advertisement Topic Structure

```
ruuvi/<GATEWAY_MAC>/<BLE_DEVICE_MAC>
```

Example: `ruuvi/C1:05:28:BF:A7:E7/6B:EF:59:3C:53:D9`

### BLE Advertisement Payload Example

```json
{
  "gw_mac": "C1:05:28:BF:A7:E7",
  "rssi": -49,
  "aoa": [],
  "gwts": 1768151705,
  "ts": 1768151705,
  "data": "07FF4C0012020001",
  "coords": ""
}
```

#### Required Fields

- `rssi` - Signal strength (integer)
- `data` - Hex string of BLE advertisement data
- `ts` or `gwts` - Unix timestamp (integer, converted to monotonic time)

### Gateway Status Topic Structure

```
ruuvi/<GATEWAY_MAC>/gw_status
```

Example: `ruuvi/C1:05:28:BF:A7:E7/gw_status`

### Gateway Status Payload Example

```json
{
  "state": "online"
}
```

or

```json
{
  "state": "offline"
}
```

The status is reflected in the `binary_sensor.<gateway>_status` entity.

## Debug Sensors

When debug entities are enabled, the following sensors are created under the Integration Device:

- **Packets Received** (`sensor.packets_received`) - Total MQTT messages received
- **Packets Forwarded** (`sensor.packets_forwarded`) - Successfully forwarded to Bluetooth backend
- **Packets Dropped** (`sensor.packets_dropped`) - Dropped due to filtering or errors
- **Active Gateways** (`sensor.active_gateways`) - Number of gateways seen in the last activity window
  - **Attributes**: Includes list of gateway MAC addresses with last seen timestamps

These sensors use Material Design Icons for consistent UI appearance.

## Diagnostics

The integration provides comprehensive diagnostics data:

1. Go to **Settings** → **Devices & Services**
2. Find **Ruuvi Gateway Bluetooth Proxy**
3. Click on the integration (not individual devices)
4. Click **Download Diagnostics**

Diagnostics include:
- Configuration (sensitive data redacted)
- Statistics counters (received, forwarded, dropped, filters)
- Gateway information (last seen timestamps, status)
- Registered scanner sources
- RSSI filter values per gateway
- Integration version and runtime info

## Troubleshooting

### MQTT Integration Not Ready

**Error:** `MQTT integration is not ready`

**Solution:** Ensure the MQTT integration is installed, configured, and connected before adding this integration.

### No Data Received

1. **Check MQTT Topics:** Verify your Ruuvi Gateway is publishing to the correct topics
   ```bash
   mosquitto_sub -h <broker> -t "ruuvi/#" -v
   ```

2. **Check Topic Prefix:** Ensure the configured prefix matches what your gateway publishes

3. **Enable Debug Logging:**
   Add to `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.ruuvi_gateway_bt_proxy: debug
   ```

### Packets Dropped

Check the debug sensors or diagnostics to see why packets are being dropped:

- `invalid_topic` - Topic doesn't match expected format
- `invalid_json` - Payload is not valid JSON
- `invalid_hex` - Data field is missing or invalid
- `filtered_gateway` - Gateway MAC not in whitelist
- `filtered_device` - Device MAC not in whitelist
- `filtered_rssi` - RSSI below minimum threshold

### Bluetooth Integration Issues

**Error:** `Bluetooth integration is not ready`

**Solution:** Ensure the Bluetooth integration is installed and functional in Home Assistant.

## Advanced Usage

### Using with Bermuda

This integration is designed to work seamlessly with the [Bermuda BLE Trilateration](https://github.com/agittins/bermuda) integration for presence detection:

1. **Install this integration** and configure it
2. **Install Bermuda** from HACS or manually
3. **Assign Areas** to the Bluetooth Proxy devices:
   - Go to Settings → Devices & Services → Ruuvi Gateway Bluetooth Proxy
   - Click on each "Ruuvi Gateway {MAC} Bluetooth Proxy" device
   - Click the pencil icon next to the device name
   - Assign the device to an Area (e.g., "Living Room", "Bedroom")
4. **Configure Bermuda** - It will automatically detect the Ruuvi Gateway scanners
5. Bermuda will use the scanner data for multilateration-based presence detection

**Important**: Bermuda requires scanners to have an assigned Area to use them for location tracking. Without an area assignment, the scanner will be detected but not used for positioning.

### Multiple Gateways

The integration automatically handles multiple Ruuvi Gateways:

- Each gateway is registered as a separate remote Bluetooth scanner with HA's Bluetooth manager
- Scanner source format: Gateway MAC address (e.g., `C1:05:28:BF:A7:E7`)
- Observations are coalesced per gateway to optimize processing
- Each gateway has its own status sensor and RSSI filter
- Gateway and Bluetooth Proxy devices are created automatically for each discovered gateway
- Device hierarchy: Gateway Device (parent) → Bluetooth Proxy Device (child)

### Custom Topic Prefixes

If your Ruuvi Gateway uses a custom topic prefix:

1. Configure the gateway to use your prefix (e.g., `custom/ruuvi/`)
2. Set the **MQTT Topic Prefix** in the integration config to match

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

```
custom_components/ruuvi_gateway_bt_proxy/
├── __init__.py              # Integration setup and entry management
├── config_flow.py           # Configuration UI flow
├── const.py                 # Constants and configuration keys
├── coordinator.py           # Main coordinator (MQTT + Bluetooth logic)
├── advertisement_parser.py  # BLE advertisement parsing
├── diagnostics.py           # Diagnostics data provider
├── sensor.py                # Optional debug sensors
├── binary_sensor.py         # Gateway status sensors
├── number.py                # Per-gateway RSSI filter entities
├── icons.json               # Material Design Icons mapping
├── manifest.json            # Integration metadata
└── translations/
    └── en.json              # English translations
```

## API Usage

This integration uses only public Home Assistant APIs:

- `homeassistant.components.mqtt.async_subscribe` - MQTT subscription for BLE advertisements and gateway status
- `homeassistant.components.bluetooth.async_register_scanner` - Registers Ruuvi Gateways as remote Bluetooth scanners
- `homeassistant.components.bluetooth.async_get_advertisement_callback` - Gets callback for forwarding advertisements
- `homeassistant.components.bluetooth.BluetoothServiceInfoBleak` - Formats advertisement data for the Bluetooth backend
- `homeassistant.helpers.device_registry` - Creates and manages device entries

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Credits

- Built for use with [Ruuvi Gateway](https://ruuvi.com/gateway/)
- Designed to complement [Bermuda BLE Trilateration](https://github.com/agittins/bermuda)

## Support

For issues, questions, or feature requests, please [open an issue on GitHub](https://github.com/eburi/hass_ruuvi_gateway_bluetooth_proxy/issues).
