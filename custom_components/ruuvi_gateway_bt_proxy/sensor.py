"""Sensor platform for Ruuvi Gateway Bluetooth Proxy integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    STAT_PACKETS_DROPPED,
    STAT_PACKETS_FORWARDED,
    STAT_PACKETS_RECEIVED,
)
from .coordinator import RuuviGatewayCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ruuvi Gateway Bluetooth Proxy sensors."""
    coordinator: RuuviGatewayCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        RuuviGatewaySensor(
            coordinator,
            entry.entry_id,
            "packets_received",
            "Packets Received",
            STAT_PACKETS_RECEIVED,
        ),
        RuuviGatewaySensor(
            coordinator,
            entry.entry_id,
            "packets_forwarded",
            "Packets Forwarded",
            STAT_PACKETS_FORWARDED,
        ),
        RuuviGatewaySensor(
            coordinator,
            entry.entry_id,
            "packets_dropped",
            "Packets Dropped",
            STAT_PACKETS_DROPPED,
        ),
        RuuviGatewayActiveGateways(coordinator, entry.entry_id),
    ]

    async_add_entities(entities)


class RuuviGatewaySensor(SensorEntity):
    """Sensor entity for Ruuvi Gateway statistics."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RuuviGatewayCoordinator,
        entry_id: str,
        sensor_id: str,
        name: str,
        stat_key: str,
    ) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._sensor_id = sensor_id
        self._stat_key = stat_key
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{sensor_id}"
        self._attr_native_unit_of_measurement = "packets"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._coordinator._stats.get(self._stat_key, 0)

    async def async_update(self) -> None:
        """Update the sensor."""
        # Stats are updated in real-time by coordinator
        pass


class RuuviGatewayActiveGateways(SensorEntity):
    """Sensor showing number of active gateways."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RuuviGatewayCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "Active Gateways"
        self._attr_unique_id = f"{entry_id}_active_gateways"
        self._attr_native_unit_of_measurement = "gateways"
        self._attr_icon = "mdi:access-point"

    @property
    def native_value(self) -> int:
        """Return the number of active gateways."""
        return len(self._coordinator._gateway_last_seen)

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """Return gateway MAC addresses as attributes."""
        return {
            "gateway_macs": list(self._coordinator._gateway_last_seen.keys()),
        }

    async def async_update(self) -> None:
        """Update the sensor."""
        # Stats are updated in real-time by coordinator
        pass
