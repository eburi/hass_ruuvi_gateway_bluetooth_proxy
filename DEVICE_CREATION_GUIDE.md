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

## Implementation for Ruuvi Gateway

### Recommended Approach for Your Integration

**Option A: Devices without entities**

If you only want to show gateway devices without creating entities:

```python
# In __init__.py async_setup_entry()

from homeassistant.helpers import device_registry as dr

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ruuvi Gateway Bluetooth Proxy from a config entry."""
    coordinator = RuuviGatewayCoordinator(hass, config)
    await coordinator.async_setup()
    
    # Create devices for discovered gateways
    device_registry = dr.async_get(hass)
    
    # You'll need to track discovered gateways in coordinator
    for gateway_mac in coordinator.discovered_gateways:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, gateway_mac)},
            connections={(dr.CONNECTION_NETWORK_MAC, gateway_mac)},
            name=f"Ruuvi Gateway {gateway_mac[-5:]}",
            manufacturer="Ruuvi",
            model="Ruuvi Gateway",
        )
```

**Option B: Devices with diagnostic entities**

If you want entities showing gateway statistics:

```python
# In sensor.py

class RuuviGatewayStatsSensor(SensorEntity):
    """Gateway statistics sensor."""
    
    def __init__(self, coordinator: RuuviGatewayCoordinator, gateway_mac: str):
        """Initialize sensor."""
        self._coordinator = coordinator
        self._gateway_mac = gateway_mac
        self._attr_unique_id = f"{gateway_mac}_stats"
        self._attr_name = f"Ruuvi Gateway {gateway_mac[-5:]} Statistics"
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._gateway_mac)},
            connections={(dr.CONNECTION_NETWORK_MAC, self._gateway_mac)},
            name=f"Ruuvi Gateway {self._gateway_mac[-5:]}",
            manufacturer="Ruuvi",
            model="Ruuvi Gateway",
        )
```

### Dynamic Gateway Discovery

Track gateways in coordinator:

```python
class RuuviGatewayCoordinator:
    """Coordinator to manage MQTT subscriptions and Bluetooth forwarding."""
    
    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.config = config
        self._gateway_info: dict[str, dict[str, Any]] = {}
        self._device_registry_callback: Callable | None = None
    
    def _mqtt_message_received(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        gateway_mac = topic_parts[-2].upper()
        
        # Track new gateway
        if gateway_mac not in self._gateway_info:
            self._gateway_info[gateway_mac] = {
                "first_seen": time.time(),
                "last_seen": time.time(),
                "packet_count": 0,
            }
            # Trigger device creation
            self.hass.async_create_task(
                self._create_gateway_device(gateway_mac)
            )
        
        self._gateway_info[gateway_mac]["last_seen"] = time.time()
        self._gateway_info[gateway_mac]["packet_count"] += 1
    
    async def _create_gateway_device(self, gateway_mac: str) -> None:
        """Create device registry entry for gateway."""
        from homeassistant.helpers import device_registry as dr
        
        device_registry = dr.async_get(self.hass)
        
        device_registry.async_get_or_create(
            config_entry_id=self._entry_id,  # Store this in __init__
            identifiers={(DOMAIN, gateway_mac)},
            connections={(dr.CONNECTION_NETWORK_MAC, gateway_mac)},
            name=f"Ruuvi Gateway {gateway_mac[-5:]}",
            manufacturer="Ruuvi",
            model="Ruuvi Gateway",
        )
        
        _LOGGER.info("Created device for gateway %s", gateway_mac)
```

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
