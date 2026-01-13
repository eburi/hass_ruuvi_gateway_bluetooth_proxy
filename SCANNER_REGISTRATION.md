# Scanner Registration Implementation

## Overview

This document describes how the Ruuvi Gateway Bluetooth Proxy integration properly registers Bluetooth scanners with Home Assistant's Bluetooth integration, matching the pattern used by ESPHome and other official integrations.

## Key Implementation Details

### Scanner Registration Flow

1. **Device Creation First**
   - Gateway device is created in the `ruuvi_gateway_bt_proxy` domain
   - Device has `identifiers` and `connections` for proper identification
   - Device ID is obtained from device registry

2. **Scanner Creation**
   - Uses `BaseHaRemoteScanner` from `habluetooth` package
   - Constructor signature: `BaseHaRemoteScanner(source, adapter, connector, connectable)`
   - Parameters:
     - `source`: Gateway MAC address (e.g., `"C1:05:28:BF:A7:E7"`)
     - `adapter`: Same as source for remote scanners
     - `connector`: `None` (passive scanning, no connection support)
     - `connectable`: `False` (passive scanning only)

3. **Scanner Registration with Bluetooth Integration**
   - Uses `async_register_scanner` from `homeassistant.components.bluetooth`
   - Parameters:
     - `hass`: Home Assistant instance
     - `scanner`: The `BaseHaRemoteScanner` instance
     - `connection_slots`: `0` (passive scanner, no connections)
     - `source_domain`: Our integration domain (`"ruuvi_gateway_bt_proxy"`)
     - `source_model`: `"Ruuvi Gateway"`
     - `source_config_entry_id`: Our config entry ID
     - `source_device_id`: Device ID from step 1

4. **Automatic Bluetooth Device Creation**
   - Bluetooth integration automatically creates a device in the `bluetooth` domain
   - This device is linked to our gateway device via `source_device_id`
   - Scanner appears in Bluetooth integration device list
   - Scanner source is the gateway MAC address

5. **Scanner Setup**
   - Call `scanner.async_setup()` to initialize the scanner
   - Store unregister callback for cleanup

## Code Reference

### In `coordinator.py`:

```python
def _ensure_scanner_registered(self, gateway_mac: str) -> None:
    """Ensure a scanner is registered for the given gateway."""
    source = gateway_mac
    
    if source not in self._registered_scanners:
        # Create device first
        self._create_gateway_device(gateway_mac)
        
        # Create scanner
        from habluetooth import BaseHaRemoteScanner
        from homeassistant.components.bluetooth import async_register_scanner
        
        scanner = BaseHaRemoteScanner(
            source,  # MAC address as source (first argument!)
            source,  # adapter - use same MAC as adapter ID
            None,    # connector - no connection support
            False,   # connectable - passive scanner only
        )
        
        # Get device ID for linking
        gateway_device_id = self._gateway_devices.get(gateway_mac)
        
        # Register with Bluetooth integration
        unregister_callback = async_register_scanner(
            self.hass,
            scanner,
            connection_slots=0,
            source_domain=DOMAIN,
            source_model="Ruuvi Gateway",
            source_config_entry_id=self.entry.entry_id,
            source_device_id=gateway_device_id,  # Links to our device
        )
        
        # Set up scanner
        scanner.async_setup()
        
        # Store for cleanup
        self._scanner_unregister_callbacks[source] = unregister_callback
        self._registered_scanners.add(source)
```

## Comparison with ESPHome

ESPHome uses the same pattern in `homeassistant/components/esphome/bluetooth.py`:

```python
def async_connect_scanner(
    hass: HomeAssistant,
    entry_data: RuntimeEntryData,
    cli: APIClient,
    device_info: DeviceInfo,
    device_id: str,
) -> CALLBACK_TYPE:
    """Connect scanner."""
    client_data = connect_scanner(cli, device_info, entry_data.available)
    scanner = client_data.scanner
    
    return partial(
        _async_unload,
        [
            async_register_scanner(
                hass,
                scanner,
                source_domain=DOMAIN,
                source_model=device_info.model,
                source_config_entry_id=entry_data.entry_id,
                source_device_id=device_id,  # Links to ESPHome device
            ),
            scanner.async_setup(),
        ],
    )
```

## Benefits of This Approach

1. **Proper Device Hierarchy**
   - Gateway device in our integration domain
   - Scanner device in Bluetooth domain
   - Proper parent-child relationship

2. **Bermuda BLE Trilateration Compatibility**
   - Scanner is recognized by Bermuda
   - Can assign area to scanner device for location tracking
   - Source is the gateway MAC, not a custom string

3. **Consistency with Official Integrations**
   - Follows the same pattern as ESPHome
   - Uses official Bluetooth integration APIs
   - Future-proof against HA changes

4. **Clean Lifecycle Management**
   - Automatic cleanup when entry is unloaded
   - Proper unregister callbacks
   - No orphaned devices or scanners

## Device Structure in HA

After implementation:

```
Ruuvi Gateway Bluetooth Proxy Integration
└── Gateway Device (ruuvi_gateway_bt_proxy domain)
    ├── Entities:
    │   ├── binary_sensor.gateway_status
    │   └── number.gateway_rssi_filter
    └── Linked Device:
        └── Bluetooth Scanner (bluetooth domain) ← Created automatically
            └── Source: C1:05:28:BF:A7:E7
```

## Common Pitfalls Avoided

1. ❌ **Wrong parameter order to `BaseHaRemoteScanner`**
   - Incorrect: `BaseHaRemoteScanner(hass, source, name, ...)`
   - Correct: `BaseHaRemoteScanner(source, adapter, connector, connectable)`

2. ❌ **Creating scanner device manually**
   - Don't create a device in your integration for the scanner
   - Let Bluetooth integration create it automatically

3. ❌ **Using custom source strings**
   - Don't use `f"ruuvi_gw_{mac.lower().replace(':', '')}"` 
   - Use the gateway MAC directly: `"C1:05:28:BF:A7:E7"`

4. ❌ **Not linking to gateway device**
   - Must pass `source_device_id` to create proper relationship
   - Device must exist before scanner registration

5. ❌ **Forgetting to call `scanner.async_setup()`**
   - Scanner won't start without this call
   - Call after registration, not before

## Testing

To verify proper scanner registration:

1. Check Bluetooth integration devices:
   - Should see scanner device with gateway MAC as source
   - Device should be linked to your gateway device

2. Check Bermuda integration:
   - Should recognize the scanner
   - Can assign area to scanner for trilateration

3. Check diagnostics:
   - Scanner source should be gateway MAC
   - No "ruuvi_gw_" prefixes anywhere

## References

- Home Assistant Bluetooth Integration: `homeassistant/components/bluetooth/`
- ESPHome Bluetooth: `homeassistant/components/esphome/bluetooth.py`
- HABluetooth Package: `habluetooth/base_scanner.py`
