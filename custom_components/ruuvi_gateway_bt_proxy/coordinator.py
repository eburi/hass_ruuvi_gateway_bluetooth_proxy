"""Coordinator for Ruuvi Gateway Bluetooth Proxy integration."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components import bluetooth, mqtt
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .advertisement_parser import parse_advertisement_data
from .const import (
    CONF_BATCH_WINDOW_MS,
    CONF_DEVICE_WHITELIST,
    CONF_GATEWAY_WHITELIST,
    CONF_QOS,
    CONF_RSSI_MIN,
    CONF_TOPIC_PREFIX,
    STAT_FILTERED_DEVICE,
    STAT_FILTERED_GATEWAY,
    STAT_FILTERED_RSSI,
    STAT_INVALID_HEX,
    STAT_INVALID_JSON,
    STAT_INVALID_TOPIC,
    STAT_PACKETS_DROPPED,
    STAT_PACKETS_FORWARDED,
    STAT_PACKETS_RECEIVED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class BLEObservation:
    """Single BLE observation from gateway."""

    gateway_mac: str
    ble_mac: str
    rssi: int
    timestamp: int
    data_hex: str
    advertisement_data: AdvertisementData | None = None


class RuuviGatewayCoordinator:
    """Coordinator to manage MQTT subscriptions and Bluetooth forwarding."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.config = config
        self._unsubscribe: Callable[[], None] | None = None
        self._flush_task: asyncio.Task | None = None
        
        # Buffers: gateway_mac -> {ble_mac -> observation}
        self._buffers: dict[str, dict[str, BLEObservation]] = defaultdict(dict)
        self._buffer_lock = asyncio.Lock()
        
        # Statistics
        self._stats: dict[str, int] = defaultdict(int)
        self._gateway_last_seen: dict[str, float] = {}
        
        # Registered scanners
        self._registered_scanners: set[str] = set()
        
        # Bluetooth callback
        self._bluetooth_callback: Callable | None = None

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Check if MQTT integration is available
        if not await mqtt.async_wait_for_ready(self.hass):
            raise ConfigEntryNotReady("MQTT integration is not ready")

        # Get Bluetooth advertisement callback
        try:
            self._bluetooth_callback = bluetooth.async_get_advertisement_callback(
                self.hass
            )
        except Exception as err:
            _LOGGER.error("Failed to get Bluetooth callback: %s", err)
            raise ConfigEntryNotReady("Bluetooth integration is not ready") from err

        # Subscribe to MQTT topics
        topic_prefix = self.config[CONF_TOPIC_PREFIX]
        qos = self.config[CONF_QOS]
        
        # Subscribe to ruuvi/<gateway_mac>/<ble_mac>
        topic_pattern = f"{topic_prefix}+/+"
        
        _LOGGER.info("Subscribing to MQTT topic: %s (QoS %d)", topic_pattern, qos)
        
        self._unsubscribe = await mqtt.async_subscribe(
            self.hass, topic_pattern, self._mqtt_message_received, qos
        )
        
        # Start flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        _LOGGER.info("Ruuvi Gateway Bluetooth Proxy coordinator started")

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        # Unsubscribe from MQTT
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        
        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        
        # Mark scanners as unavailable (best effort)
        for source in self._registered_scanners:
            _LOGGER.debug("Scanner %s unregistered", source)
        
        self._registered_scanners.clear()
        
        _LOGGER.info("Ruuvi Gateway Bluetooth Proxy coordinator shut down")

    @callback
    def _mqtt_message_received(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        self._stats[STAT_PACKETS_RECEIVED] += 1
        
        try:
            # Parse topic: ruuvi/<gateway_mac>/<ble_mac>
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 3:
                _LOGGER.debug("Invalid topic format: %s", msg.topic)
                self._stats[STAT_INVALID_TOPIC] += 1
                self._stats[STAT_PACKETS_DROPPED] += 1
                return
            
            gateway_mac = topic_parts[-2].upper()
            ble_mac = topic_parts[-1].upper()
            
            # Parse JSON payload
            try:
                payload = json.loads(msg.payload)
            except json.JSONDecodeError as err:
                _LOGGER.debug("Invalid JSON in topic %s: %s", msg.topic, err)
                self._stats[STAT_INVALID_JSON] += 1
                self._stats[STAT_PACKETS_DROPPED] += 1
                return
            
            # Extract fields
            rssi = payload.get("rssi", 0)
            timestamp = payload.get("ts", payload.get("gwts", int(time.time())))
            data_hex = payload.get("data", "")
            
            # Validate hex data
            if not data_hex or not isinstance(data_hex, str):
                _LOGGER.debug("Missing or invalid data field in topic %s", msg.topic)
                self._stats[STAT_INVALID_HEX] += 1
                self._stats[STAT_PACKETS_DROPPED] += 1
                return
            
            # Apply filters
            if not self._should_process(gateway_mac, ble_mac, rssi):
                return
            
            # Create observation
            observation = BLEObservation(
                gateway_mac=gateway_mac,
                ble_mac=ble_mac,
                rssi=rssi,
                timestamp=timestamp,
                data_hex=data_hex,
            )
            
            # Buffer the observation
            asyncio.create_task(self._buffer_observation(observation))
            
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error processing MQTT message: %s", err)
            self._stats[STAT_PACKETS_DROPPED] += 1

    def _should_process(self, gateway_mac: str, ble_mac: str, rssi: int) -> bool:
        """Check if observation should be processed based on filters."""
        # Gateway whitelist
        gateway_whitelist = self.config.get(CONF_GATEWAY_WHITELIST, [])
        if gateway_whitelist and gateway_mac not in gateway_whitelist:
            self._stats[STAT_FILTERED_GATEWAY] += 1
            self._stats[STAT_PACKETS_DROPPED] += 1
            return False
        
        # Device whitelist
        device_whitelist = self.config.get(CONF_DEVICE_WHITELIST, [])
        if device_whitelist and ble_mac not in device_whitelist:
            self._stats[STAT_FILTERED_DEVICE] += 1
            self._stats[STAT_PACKETS_DROPPED] += 1
            return False
        
        # RSSI filter
        rssi_min = self.config.get(CONF_RSSI_MIN, -127)
        if rssi < rssi_min:
            self._stats[STAT_FILTERED_RSSI] += 1
            self._stats[STAT_PACKETS_DROPPED] += 1
            return False
        
        return True

    async def _buffer_observation(self, observation: BLEObservation) -> None:
        """Buffer an observation for batching."""
        async with self._buffer_lock:
            gateway_buffer = self._buffers[observation.gateway_mac]
            
            # Keep most recent or highest RSSI
            existing = gateway_buffer.get(observation.ble_mac)
            if existing is None or observation.rssi >= existing.rssi:
                gateway_buffer[observation.ble_mac] = observation
            
            # Update last seen timestamp
            self._gateway_last_seen[observation.gateway_mac] = time.time()

    async def _flush_loop(self) -> None:
        """Periodically flush buffered observations."""
        batch_window_ms = self.config.get(CONF_BATCH_WINDOW_MS, 250)
        interval = batch_window_ms / 1000.0
        
        while True:
            try:
                await asyncio.sleep(interval)
                await self._flush_buffers()
            except asyncio.CancelledError:
                break
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Error in flush loop: %s", err)

    async def _flush_buffers(self) -> None:
        """Flush all buffered observations to Bluetooth backend."""
        async with self._buffer_lock:
            for gateway_mac, gateway_buffer in self._buffers.items():
                if not gateway_buffer:
                    continue
                
                # Ensure scanner is registered for this gateway
                self._ensure_scanner_registered(gateway_mac)
                
                # Process each buffered observation
                for observation in gateway_buffer.values():
                    await self._forward_to_bluetooth(observation)
                
                # Clear buffer
                gateway_buffer.clear()

    def _ensure_scanner_registered(self, gateway_mac: str) -> None:
        """Ensure a scanner is registered for the given gateway."""
        source = f"ruuvi_gw_{gateway_mac.replace(':', '').lower()}"
        
        if source not in self._registered_scanners:
            # Register scanner
            scanner = bluetooth.HaBluetoothConnector(
                client=None,  # We're a passive scanner
                source=source,
                adapter=gateway_mac,
            )
            
            bluetooth.async_register_scanner(
                self.hass, scanner, connection_slots=0
            )
            
            self._registered_scanners.add(source)
            _LOGGER.info("Registered Bluetooth scanner for gateway %s", gateway_mac)

    async def _forward_to_bluetooth(self, observation: BLEObservation) -> None:
        """Forward a single observation to the Bluetooth backend."""
        try:
            # Parse advertisement data
            if observation.advertisement_data is None:
                observation.advertisement_data = parse_advertisement_data(
                    observation.data_hex
                )
            
            # Create BLEDevice
            device = BLEDevice(
                address=observation.ble_mac,
                name=observation.advertisement_data.local_name,
                details={},
                rssi=observation.rssi,
            )
            
            # Update RSSI in advertisement data
            advertisement_data = AdvertisementData(
                local_name=observation.advertisement_data.local_name,
                manufacturer_data=observation.advertisement_data.manufacturer_data,
                service_data=observation.advertisement_data.service_data,
                service_uuids=observation.advertisement_data.service_uuids,
                rssi=observation.rssi,
                tx_power=observation.advertisement_data.tx_power,
                platform_data=observation.advertisement_data.platform_data,
            )
            
            # Create service info
            source = f"ruuvi_gw_{observation.gateway_mac.replace(':', '').lower()}"
            service_info = BluetoothServiceInfoBleak(
                name=advertisement_data.local_name or observation.ble_mac,
                address=observation.ble_mac,
                rssi=observation.rssi,
                manufacturer_data=advertisement_data.manufacturer_data,
                service_data=advertisement_data.service_data,
                service_uuids=advertisement_data.service_uuids,
                source=source,
                device=device,
                advertisement=advertisement_data,
                connectable=False,
                time=observation.timestamp,
                tx_power=advertisement_data.tx_power,
            )
            
            # Forward to Bluetooth backend
            if self._bluetooth_callback:
                self._bluetooth_callback(service_info)
                self._stats[STAT_PACKETS_FORWARDED] += 1
            else:
                _LOGGER.warning("Bluetooth callback not available")
                
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error forwarding to Bluetooth: %s", err)
            self._stats[STAT_PACKETS_DROPPED] += 1

    def get_diagnostics(self) -> dict[str, Any]:
        """Get diagnostics data."""
        return {
            "config": {
                CONF_TOPIC_PREFIX: self.config.get(CONF_TOPIC_PREFIX),
                CONF_QOS: self.config.get(CONF_QOS),
                CONF_BATCH_WINDOW_MS: self.config.get(CONF_BATCH_WINDOW_MS),
                CONF_RSSI_MIN: self.config.get(CONF_RSSI_MIN),
                "gateway_whitelist_count": len(
                    self.config.get(CONF_GATEWAY_WHITELIST, [])
                ),
                "device_whitelist_count": len(
                    self.config.get(CONF_DEVICE_WHITELIST, [])
                ),
            },
            "statistics": dict(self._stats),
            "gateways": {
                mac: {
                    "last_seen": last_seen,
                    "source": f"ruuvi_gw_{mac.replace(':', '').lower()}",
                }
                for mac, last_seen in self._gateway_last_seen.items()
            },
            "registered_scanners": list(self._registered_scanners),
        }
