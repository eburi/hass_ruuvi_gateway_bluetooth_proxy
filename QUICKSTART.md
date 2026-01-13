# Quick Start Guide

## Installation

### Option 1: Manual Installation

1. Copy the `custom_components/ruuvi_gateway_bt_proxy` folder to your Home Assistant `custom_components` directory:
   ```bash
   cd /config  # or wherever your HA config is
   mkdir -p custom_components
   cp -r hass_ruuvi_gateway_bluetooth_proxy/custom_components/ruuvi_gateway_bt_proxy custom_components/
   ```

2. Restart Home Assistant

### Option 2: HACS Installation

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add `https://github.com/eburi/hass_ruuvi_gateway_bluetooth_proxy` as an Integration
5. Search for "Ruuvi Gateway Bluetooth Proxy"
6. Install
7. Restart Home Assistant

## Prerequisites

Before adding this integration, ensure you have:

1. ✅ **MQTT Integration configured** in Home Assistant
   - Settings → Devices & Services → Add Integration → MQTT
   - Connected to your MQTT broker

2. ✅ **Ruuvi Gateway configured** to publish to MQTT
   - Gateway connected to same MQTT broker
   - Publishing BLE advertisements

## Setup

1. **Add Integration**
   ```
   Settings → Devices & Services → Add Integration
   Search: "Ruuvi Gateway Bluetooth Proxy"
   ```

2. **Basic Configuration** (recommended to start)
   - MQTT Topic Prefix: `ruuvi/` (default)
   - MQTT QoS: `0` (default)
   - Gateway Whitelist: (leave empty)
   - Device Whitelist: (leave empty)
   - Minimum RSSI: `-127` (default, no filtering)
   - Batch Window: `250` ms (default)
   - Enable Debug Entity: `✓` (check this to monitor)

3. **Save and Verify**
   - Check debug sensors appear:
     - `sensor.ruuvi_gateway_bt_proxy_packets_received`
     - `sensor.ruuvi_gateway_bt_proxy_packets_forwarded`
     - `sensor.ruuvi_gateway_bt_proxy_packets_dropped`
     - `sensor.ruuvi_gateway_bt_proxy_active_gateways`

## Verification

### 1. Check MQTT Messages

Use an MQTT client to verify your gateway is publishing:

```bash
mosquitto_sub -h YOUR_BROKER -t "ruuvi/#" -v
```

Expected output:
```
ruuvi/C1:05:28:BF:A7:E7/6B:EF:59:3C:53:D9 {"gw_mac":"C1:05:28:BF:A7:E7","rssi":-49,...}
```

### 2. Check Debug Sensors

Go to Developer Tools → States and check:
- `sensor.ruuvi_gateway_bt_proxy_packets_received` should be increasing
- `sensor.ruuvi_gateway_bt_proxy_active_gateways` should show your gateway count

### 3. Check Diagnostics

Settings → Devices & Services → Ruuvi Gateway Bluetooth Proxy → Device → Download Diagnostics

Should show:
```json
{
  "statistics": {
    "packets_received": 123,
    "packets_forwarded": 120,
    "packets_dropped": 3
  },
  "gateways": {
    "C1:05:28:BF:A7:E7": {
      "last_seen": 1768151705.123,
      "source": "C1:05:28:BF:A7:E7"
    }
  }
}
```

### 4. Check Bluetooth Integration

Settings → Devices & Services → Bluetooth

You should see:
- A Bluetooth scanner device for each Ruuvi Gateway (in the `bluetooth` domain)
- Scanner source will be the gateway MAC (e.g., `C1:05:28:BF:A7:E7`)
- Scanner device is automatically linked to the gateway device created by this integration
- Bluetooth devices being detected from your Ruuvi Gateway scanners

## Troubleshooting

### No Packets Received

1. **Verify MQTT is working**
   ```bash
   mosquitto_sub -h YOUR_BROKER -t "ruuvi/#" -v
   ```
   If no output → problem is with gateway or broker

2. **Check topic prefix matches**
   - Integration config must match what gateway publishes
   - Default is `ruuvi/`

3. **Enable debug logging**
   Add to `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.ruuvi_gateway_bt_proxy: debug
   ```
   Restart and check logs for MQTT subscription details

### Packets Dropped

Check diagnostics to see why:
- `invalid_json` → Gateway publishing malformed JSON
- `invalid_hex` → Data field missing or invalid
- `filtered_gateway` → Gateway MAC not in whitelist
- `filtered_device` → Device MAC not in whitelist
- `filtered_rssi` → RSSI below threshold

### Not Showing in Bluetooth

1. Check Bluetooth integration is installed and working
2. Check packets are being forwarded (debug sensor)
3. Check Home Assistant logs for Bluetooth errors

## Advanced Configuration

### Filter by Gateway

Only accept data from specific gateways:
```
Gateway Whitelist: C1:05:28:BF:A7:E7, AA:BB:CC:DD:EE:FF
```

### Filter by Device

Only accept specific BLE devices:
```
Device Whitelist: 6B:EF:59:3C:53:D9
```

### Filter by Signal Strength

Only accept strong signals:
```
Minimum RSSI: -80
```
(Range: -127 to 0, where 0 is strongest)

### Adjust Batching

Higher batch window = less CPU, more latency:
```
Batch Window: 500 ms
```

Lower batch window = more responsive, more CPU:
```
Batch Window: 100 ms
```

## Integration with Bermuda

This integration is designed to work with [Bermuda](https://github.com/agittins/bermuda) for presence detection:

1. Install this integration first
2. Verify it's receiving and forwarding packets
3. Install Bermuda from HACS
4. Configure Bermuda - it will automatically detect the Ruuvi Gateway scanners
5. Add BLE devices (like phones, tags) to track in Bermuda

## Next Steps

- Configure room/area assignments for gateways in HA
- Set up Bermuda for presence detection
- Create automations based on BLE presence
- Monitor statistics with debug sensors

## Support

For issues or questions:
- Check the [README.md](README.md) for detailed documentation
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- [Open an issue on GitHub](https://github.com/eburi/hass_ruuvi_gateway_bluetooth_proxy/issues)
