# Ruuvi Gateway Bluetooth Proxy

A Home Assistant custom integration that subscribes to MQTT topics published by Ruuvi Gateways and forwards BLE advertisements to Home Assistant's Bluetooth backend.

## ⚠️ Important: MQTT Integration Dependency

**This integration uses Home Assistant's built-in MQTT integration. It does not connect to MQTT directly.**

You must have the MQTT integration configured and connected in Home Assistant before using this integration.

## Features

- 🔌 **Uses HA's Built-in MQTT** - No external MQTT libraries, relies on Home Assistant's existing MQTT connection
- 📡 **External Scanner Registration** - Registers each Ruuvi Gateway as a Bluetooth scanner source
- 🎯 **Flexible Filtering** - Whitelist gateways and devices, filter by RSSI
- 📦 **Intelligent Batching** - Coalesces observations within a configurable window to reduce processing
- 📊 **Diagnostics & Debug Sensors** - Optional sensors for monitoring packet statistics
- 🔧 **Full Config Flow** - Easy setup and configuration through the UI

## How It Works

1. **Ruuvi Gateway** publishes BLE advertisements to MQTT topics in format: `ruuvi/<gateway_mac>/<ble_device_mac>`
2. **This Integration** subscribes to those topics using HA's MQTT integration
3. **Parses & Forwards** - Parses the BLE advertisement data and forwards it to HA's Bluetooth backend
4. **Other Integrations** - Bluetooth-based integrations (like Bermuda for presence detection) can use the data

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
| **Minimum RSSI** | `-127` | Drop packets with RSSI below this value |
| **Batch Window (ms)** | `250` | Time window for coalescing observations (50-5000ms) |
| **Enable Debug Entity** | `false` | Enable debug sensors for monitoring statistics |

### Example Configuration

**Basic setup:**
- Topic Prefix: `ruuvi/`
- All other options at defaults

**Filtered setup:**
- Topic Prefix: `ruuvi/`
- Gateway Whitelist: `C1:05:28:BF:A7:E7, AA:BB:CC:DD:EE:FF`
- Device Whitelist: `6B:EF:59:3C:53:D9`
- Minimum RSSI: `-80`
- Batch Window: `500`
- Enable Debug Entity: `✓`

## MQTT Topic Format

The integration subscribes to topics matching:

```
<prefix>+/+
```

Default: `ruuvi/+/+`

### Topic Structure

```
ruuvi/<GATEWAY_MAC>/<BLE_DEVICE_MAC>
```

Example: `ruuvi/C1:05:28:BF:A7:E7/6B:EF:59:3C:53:D9`

### Payload Example

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
- `ts` or `gwts` - Unix timestamp (integer)

## Debug Sensors

When debug entities are enabled, the following sensors are created:

- **Packets Received** - Total MQTT messages received
- **Packets Forwarded** - Successfully forwarded to Bluetooth backend
- **Packets Dropped** - Dropped due to filtering or errors
- **Active Gateways** - Number of gateways seen (with MAC list in attributes)

## Diagnostics

The integration provides comprehensive diagnostics data:

1. Go to **Settings** → **Devices & Services**
2. Find **Ruuvi Gateway Bluetooth Proxy**
3. Click on the device
4. Click **Download Diagnostics**

Diagnostics include:
- Configuration (redacted)
- Statistics counters
- Gateway information
- Registered scanner sources

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

1. Install and configure this integration
2. Install Bermuda
3. Bermuda will automatically detect the Ruuvi Gateway scanners
4. Configure Bermuda to use the scanner data for presence detection

### Multiple Gateways

The integration automatically handles multiple Ruuvi Gateways:

- Each gateway is registered as a separate Bluetooth scanner source
- Source name format: `ruuvi_gw_<mac_without_colons>`
- Observations are coalesced per gateway to optimize processing

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
└── sensor.py               # Optional debug sensors
```

## API Usage

This integration uses only public Home Assistant APIs:

- `homeassistant.components.mqtt.async_subscribe` - MQTT subscription
- `homeassistant.components.bluetooth.async_register_scanner` - Scanner registration
- `homeassistant.components.bluetooth.async_get_advertisement_callback` - Advertisement forwarding

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
