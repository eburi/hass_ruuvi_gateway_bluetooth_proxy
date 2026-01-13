# Home Assistant Device Registry Guide

## Overview

This guide explains how to create devices in Home Assistant's device registry for Bluetooth scanners (Ruuvi Gateways). Based on research of Home Assistant core integrations (ESPHome, MQTT, Bluetooth).

## Key Concepts

### What is a Device?

- A **device** represents a physical device with its own control unit or a service
- Devices appear in Home Assistant's device registry and can be browsed in the UI
- Multiple entities can belong to a single device
- Devices can have parent-child relationships using `via_device`

### Device Registry Properties

Key properties for device creation:

| Property | Description | Required |
|----------|-------------|----------|
| `identifiers` | Set of (domain, id) tuples that uniquely identify the device | Yes (or connections) |
| `connections` | Set of (connection_type, identifier) tuples for network connections | Yes (or identifiers) |
| `name` | Device name | Recommended |
| `manufacturer` | Device manufacturer | Recommended |
| `model` | Device model name | Recommended |
| `sw_version` | Firmware/software version | Optional |
| `hw_version` | Hardware version | Optional |
| `configuration_url` | URL to configure the device | Optional |
| `via_device` | Parent device identifier (for sub-devices) | Optional |
| `suggested_area` | Suggested area placement | Optional |

## Two Methods to Create Devices

### Method 1: Automatic via Entity's `device_info` Property

**When to use:** When you have entities (sensors, switches, etc.) that belong to the device

The simplest method - devices are automatically created when entities are registered with `device_info`:

```python
from homeassistant.helpers.entity import DeviceInfo

class MyEntity(SensorEntity):
    """Example entity."""
    
    def __init__(self, gateway_mac: str):
        """Initialize the entity."""
        self._gateway_mac = gateway_mac
        self._attr_unique_id = f"{gateway_mac}_signal"
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._gateway_mac)},
            name=f"Ruuvi Gateway {self._gateway_mac}",
            manufacturer="Ruuvi",
            model="Ruuvi Gateway",
            sw_version="1.0.0",
            configuration_url=f"http://{self._gateway_mac}.local",
        )
```

**Key points:**
- Entity MUST have a `unique_id` property
- Entity MUST be loaded via a config entry
- Device is automatically created/updated when entity is added
- Multiple entities with the same `identifiers` will be grouped under one device

### Method 2: Manual via `device_registry.async_get_or_create()`

**When to use:** When you need to create devices without entities (e.g., hub/gateway devices)

Direct device creation without entities:

```python
from homeassistant.helpers import device_registry as dr

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    
    # Get device registry
    device_registry = dr.async_get(hass)
    
    # Create device for each gateway
    gateway_mac = "AA:BB:CC:DD:EE:FF"
    
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, gateway_mac)},
        connections={(dr.CONNECTION_NETWORK_MAC, gateway_mac)},
        name=f"Ruuvi Gateway {gateway_mac}",
        manufacturer="Ruuvi",
        model="Ruuvi Gateway",
        sw_version="1.0.0",
        configuration_url=f"http://{gateway_mac}.local",
        suggested_area="Living Room",
    )
    
    # Store device_id for later use
    device_id = device_entry.id
```

## Real-World Example: ESPHome Integration

From `homeassistant/components/esphome/manager.py`:

```python
@callback
def _async_setup_device_registry(
    hass: HomeAssistant, 
    entry: ESPHomeConfigEntry, 
    entry_data: RuntimeEntryData
) -> str:
    """Set up device registry feature for a particular config entry."""
    device_info = entry_data.device_info
    device_registry = dr.async_get(hass)
    
    # Create main device
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        configuration_url=configuration_url,
        connections={(dr.CONNECTION_NETWORK_MAC, device_info.mac_address)},
        name=entry_data.friendly_name or entry_data.name,
        manufacturer=manufacturer,
        model=model,
        sw_version=sw_version,
        suggested_area=suggested_area,
    )
    
    # Handle sub devices with via_device
    for sub_device in device_info.devices:
        sub_device_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{device_info.mac_address}_{sub_device.device_id}")},
            name=sub_device.name or device_entry.name,
            manufacturer=manufacturer,
            model=model,
            sw_version=sw_version,
            suggested_area=sub_device_suggested_area,
        )
        
        # Update the sub device to set via_device_id
        device_registry.async_update_device(
            sub_device_entry.id,
            via_device_id=device_entry.id,
        )
    
    return device_entry.id
```

## Parent-Child Device Relationships

Use `via_device` to create hierarchical device structures:

```python
# Create parent device (hub/gateway)
parent_device = device_registry.async_get_or_create(
    config_entry_id=entry.entry_id,
    identifiers={(DOMAIN, "hub_001")},
    name="Main Hub",
    manufacturer="Ruuvi",
    model="Gateway",
)

# Create child device (connected sensor)
child_device = device_registry.async_get_or_create(
    config_entry_id=entry.entry_id,
    identifiers={(DOMAIN, "sensor_001")},
    name="Temperature Sensor",
    manufacturer="Ruuvi",
    model="RuuviTag",
    via_device=(DOMAIN, "hub_001"),  # Links to parent
)
```

## Connection Types

Common connection types from `device_registry`:

```python
CONNECTION_BLUETOOTH = "bluetooth"
CONNECTION_NETWORK_MAC = "mac"
CONNECTION_UPNP = "upnp"
CONNECTION_ZIGBEE = "zigbee"
CONNECTION_ZWAVE = "zwave"
```

## Identifiers vs Connections

**Identifiers:**
- Domain-specific IDs: `(DOMAIN, serial_number)`
- Must be unique within your domain
- Use for logical device identification

**Connections:**
- Physical connection IDs: `(CONNECTION_NETWORK_MAC, mac_address)`
- Must be globally unique across all integrations
- Use for physical device identification

**Best practice:** Provide both when possible:
```python
device_registry.async_get_or_create(
    config_entry_id=entry.entry_id,
    identifiers={(DOMAIN, gateway_mac)},  # Domain-specific
    connections={(dr.CONNECTION_NETWORK_MAC, gateway_mac)},  # Physical
    name="My Gateway",
)
```

## Updating Devices

Use `async_update_device()` to modify existing devices:

```python
device_registry = dr.async_get(hass)

# Update device properties
device_registry.async_update_device(
    device_id,
    sw_version="2.0.0",
    name="New Name",
    suggested_area="Bedroom",
)
```

## Removing Devices

Implement `async_remove_config_entry_device` in `__init__.py`:

```python
async def async_remove_config_entry_device(
    hass: HomeAssistant, 
    config_entry: ConfigEntry, 
    device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    # Perform cleanup
    # Return True if successful, False to prevent removal
    return True
```

## Device Info Categories

Device info is categorized as **Link**, **Primary**, or **Secondary**:

**Primary** (full device info):
- Must include: identifiers/connections, manufacturer, model, name
- Optional: configuration_url, sw_version, hw_version, suggested_area, via_device

**Link** (minimal info):
- Only connections and/or identifiers
- Used for device linking without full registration

**Secondary** (default fallbacks):
- Uses default_manufacturer, default_model, default_name
- Values overridden if primary values set later

## Implementation for Ruuvi Gateway Bluetooth Proxy

### Current Implementation (Working)

Our integration uses **Method 2** (manual device creation) combined with **automatic Bluetooth scanner registration**.

#### Device Structure

```
Ruuvi Gateway Bluetooth Proxy Integration
└── Gateway Device (ruuvi_gateway_bt_proxy domain)
    ├── Created manually via device_registry.async_get_or_create()
    ├── Entities:
    │   ├── binary_sensor.gateway_status (online/offline)
    │   └── number.gateway_rssi_filter (per-gateway RSSI threshold)
    └── Linked Device:
        └── Bluetooth Scanner (bluetooth domain)
            ├── Created automatically by Bluetooth integration
            ├── Linked via source_device_id
            └── Source: <gateway_mac>
```

#### Implementation in coordinator.py

```python
def _ensure_scanner_registered(self, gateway_mac: str) -> None:
    """Ensure a scanner is registered for the given gateway."""
    source = gateway_mac
    
    if source not in self._registered_scanners:
        # Step 1: Create gateway device first
        self._create_gateway_device(gateway_mac)
        
        # Step 2: Create and register scanner
        from habluetooth import BaseHaRemoteScanner
        from homeassistant.components.bluetooth import async_register_scanner
        
        scanner = BaseHaRemoteScanner(
            source,  # MAC address as source
            source,  # adapter - use same MAC
            None,    # connector - no connection support
            False,   # connectable - passive scanner only
        )
        
        # Get device ID for linking
        gateway_device_id = self._gateway_devices.get(gateway_mac)
        
        # Step 3: Register scanner with Bluetooth integration
        # This automatically creates a scanner device in bluetooth domain
        unregister_callback = async_register_scanner(
            self.hass,
            scanner,
            connection_slots=0,
            source_domain=DOMAIN,  # Our integration domain
            source_model="Ruuvi Gateway",
            source_config_entry_id=self.entry.entry_id,
            source_device_id=gateway_device_id,  # Links to our device
        )
        
        # Step 4: Set up the scanner
        scanner.async_setup()
        
        # Store for cleanup
        self._scanner_unregister_callbacks[source] = unregister_callback
        self._registered_scanners.add(source)

def _create_gateway_device(self, gateway_mac: str) -> None:
    """Create a device entry for a Ruuvi Gateway."""
    if gateway_mac in self._gateway_devices:
        return
    
    device_registry = dr.async_get(self.hass)
    
    # Create gateway device
    gateway_device = device_registry.async_get_or_create(
        config_entry_id=self.entry.entry_id,
        identifiers={(DOMAIN, gateway_mac)},
        connections={(dr.CONNECTION_NETWORK_MAC, gateway_mac)},
        name=f"Ruuvi Gateway {gateway_mac}",
        manufacturer="Ruuvi",
        model="Ruuvi Gateway",
    )
    
    # Note: Bluetooth scanner device is automatically created by
    # Bluetooth integration when we call async_register_scanner
    # with source_device_id parameter
    
    self._gateway_devices[gateway_mac] = gateway_device.id
```

#### Key Points

1. **Gateway Device** - Created manually in our integration domain
   - Has entities for status and RSSI filter
   - Visible in our integration's device list

2. **Scanner Device** - Created automatically by Bluetooth integration
   - Created when `async_register_scanner` is called with `source_device_id`
   - Appears in Bluetooth integration's device list
   - Linked to gateway device via `source_device_id`
   - Source is the gateway MAC address

3. **Why This Works**
   - Matches ESPHome pattern for Bluetooth proxy devices
   - Bermuda and other integrations recognize the scanner
   - Clean separation of concerns (gateway vs scanner)
   - Proper parent-child relationship via linking

4. **Common Mistakes to Avoid**
   - ❌ Don't manually create a device for the scanner in your domain
   - ❌ Don't use custom source strings like `"ruuvi_gw_<mac>"`
   - ❌ Don't forget to pass `source_device_id` to link devices
   - ✅ Do let Bluetooth integration create the scanner device
   - ✅ Do use gateway MAC directly as source
   - ✅ Do create gateway device before registering scanner

## Best Practices

1. **Always provide unique identifiers**
   - Use MAC addresses or serial numbers
   - Format consistently (uppercase MAC addresses)

2. **Use both identifiers and connections**
   - Helps with device matching and discovery
   - Makes devices more robust

3. **Provide meaningful names**
   - Include identifiable information
   - Use friendly formatting

4. **Store config_entry_id**
   - Ensures devices are linked to your integration
   - Enables proper cleanup on removal

5. **Handle dynamic discovery**
   - Create devices when first seen
   - Update last-seen timestamps
   - Clean up stale devices

6. **Use via_device for hierarchies**
   - Shows device relationships in UI
   - Enables logical grouping

7. **Provide configuration_url when possible**
   - Improves user experience
   - Enables quick access to device settings

## References

- [Device Registry Documentation](https://developers.home-assistant.io/docs/device_registry_index)
- [ESPHome Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/esphome)
- [Entity Integration Guide](https://developers.home-assistant.io/docs/entity_registry_index)
