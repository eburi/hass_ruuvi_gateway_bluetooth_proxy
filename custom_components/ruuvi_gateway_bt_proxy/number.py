"""Number platform for Ruuvi Gateway Bluetooth Proxy integration."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RuuviGatewayCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ruuvi Gateway RSSI filter numbers."""
    coordinator: RuuviGatewayCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Register callback to create number entities for new gateways
    coordinator.register_gateway_discovered_callback(
        lambda gateway_mac: _async_add_gateway_number(
            hass, entry, coordinator, async_add_entities, gateway_mac
        )
    )

    # Create numbers for existing gateways
    entities = []
    for gateway_mac in coordinator.get_gateway_macs():
        entities.append(RuuviGatewayRSSIFilter(coordinator, entry, gateway_mac))

    if entities:
        async_add_entities(entities)


@callback
def _async_add_gateway_number(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RuuviGatewayCoordinator,
    async_add_entities: AddEntitiesCallback,
    gateway_mac: str,
) -> None:
    """Add number entity for a newly discovered gateway."""
    async_add_entities([RuuviGatewayRSSIFilter(coordinator, entry, gateway_mac)])


class RuuviGatewayRSSIFilter(NumberEntity):
    """Number entity for per-gateway RSSI filter threshold."""

    _attr_has_entity_name = True
    _attr_native_min_value = -127
    _attr_native_max_value = 0
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:signal"

    def __init__(
        self,
        coordinator: RuuviGatewayCoordinator,
        entry: ConfigEntry,
        gateway_mac: str,
    ) -> None:
        """Initialize the RSSI filter number."""
        self._coordinator = coordinator
        self._entry = entry
        self._gateway_mac = gateway_mac
        self._attr_name = "RSSI Filter"
        self._attr_unique_id = f"{entry.entry_id}_{gateway_mac}_rssi_filter"

        # Set device info to link to gateway device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, gateway_mac)},
        }

        # Initialize with default or stored value
        self._attr_native_value = coordinator.get_gateway_rssi_filter(gateway_mac)

    @property
    def native_value(self) -> float:
        """Return the current RSSI filter value."""
        return self._coordinator.get_gateway_rssi_filter(self._gateway_mac)

    async def async_set_native_value(self, value: float) -> None:
        """Set the RSSI filter value."""
        self._coordinator.set_gateway_rssi_filter(self._gateway_mac, int(value))
        self.async_write_ha_state()
        _LOGGER.info(
            "Updated RSSI filter for gateway %s to %d",
            self._gateway_mac,
            int(value),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._gateway_mac in self._coordinator.get_gateway_macs()
