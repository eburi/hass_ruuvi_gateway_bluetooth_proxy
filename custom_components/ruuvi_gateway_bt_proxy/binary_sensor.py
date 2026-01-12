"""Binary Sensor platform for Ruuvi Gateway Bluetooth Proxy integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RuuviGatewayCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ruuvi Gateway Bluetooth Proxy binary sensors."""
    coordinator: RuuviGatewayCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create binary sensors for existing gateways
    entities = []
    for gateway_mac in coordinator.get_gateway_macs():
        entities.append(
            RuuviGatewayStatusSensor(coordinator, entry.entry_id, gateway_mac)
        )

    if entities:
        async_add_entities(entities)

    # Register callback for newly discovered gateways
    @callback
    def _gateway_discovered(gateway_mac: str) -> None:
        """Handle newly discovered gateway."""
        async_add_entities(
            [RuuviGatewayStatusSensor(coordinator, entry.entry_id, gateway_mac)]
        )

    coordinator.register_gateway_discovered_callback(_gateway_discovered)


class RuuviGatewayStatusSensor(BinarySensorEntity):
    """Binary sensor showing gateway online/offline status."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: RuuviGatewayCoordinator,
        entry_id: str,
        gateway_mac: str,
    ) -> None:
        """Initialize the binary sensor."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._gateway_mac = gateway_mac
        self._attr_name = "Status"
        self._attr_unique_id = f"{gateway_mac}_status"

    @property
    def device_info(self):
        """Return device info to link sensor to gateway device."""
        return {
            "identifiers": {(DOMAIN, self._gateway_mac)},
            "connections": {(dr.CONNECTION_NETWORK_MAC, self._gateway_mac)},
            "name": f"Ruuvi Gateway {self._gateway_mac}",
            "manufacturer": "Ruuvi",
            "model": "Ruuvi Gateway",
        }

    @property
    def is_on(self) -> bool:
        """Return true if gateway is online."""
        return self._coordinator._gateway_status.get(self._gateway_mac, False)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Entity is available if we've ever seen this gateway
        return self._gateway_mac in self._coordinator._gateway_last_seen

    async def async_update(self) -> None:
        """Update the sensor."""
        # Status is updated in real-time by coordinator
        pass

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Force update
        self.async_write_ha_state()
