"""Coordinator for Ruuvi Gateway Bluetooth Proxy integration."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from homeassistant.components import bluetooth, mqtt
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .advertisement_parser import parse_advertisement_data
from .const import (
    CONF_BATCH_WINDOW_MS,
    CONF_DEVICE_WHITELIST,
    CONF_GATEWAY_WHITELIST,
    CONF_QOS,
    CONF_RSSI_MIN,
    CONF_TOPIC_PREFIX,
    DOMAIN,
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
    timestamp: float  # Monotonic time
    data_hex: str
    advertisement_data: AdvertisementData | None = None


class RuuviGatewayCoordinator:
    """Coordinator to manage MQTT subscriptions and Bluetooth forwarding."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, config: dict[str, Any]
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.config = config
        self._unsubscribe: Callable[[], None] | None = None
        self._flush_task: asyncio.Task | None = None

        # Buffers: gateway_mac -> {ble_mac -> observation}
        self._buffers: dict[str, dict[str, BLEObservation]] = defaultdict(dict)
        self._buffer_lock = asyncio.Lock()

        # Calculate offset between epoch and monotonic time at startup
        self._time_offset = time.time() - time.monotonic()

        # Statistics
        self._stats: dict[str, int] = defaultdict(int)
        self._gateway_last_seen: dict[str, float] = {}
        self._gateway_status: dict[str, bool] = {}  # gateway_mac -> online status

        # Registered scanners and devices
        self._registered_scanners: set[str] = set()
        self._scanner_unregister_callbacks: dict[
            str, Callable[[], None]
        ] = {}  # source -> unregister callback
        self._gateway_devices: dict[str, str] = {}  # gateway_mac -> device_id
        self._device_registry: dr.DeviceRegistry | None = None

        # Per-gateway RSSI filters
        self._gateway_rssi_filters: dict[str, int] = {}  # gateway_mac -> rssi_min
        self._gateway_discovered_callbacks: list[Callable[[str], None]] = []

        # Background tasks
        self._background_tasks: set[asyncio.Task] = set()

        # Bluetooth callback
        self._bluetooth_callback: Callable | None = None

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        # Get device registry
        self._device_registry = dr.async_get(self.hass)

        # Check if MQTT integration is available
        if not self.hass.data.get(mqtt.DATA_MQTT):
            raise ConfigEntryNotReady("MQTT integration is not set up")

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

        try:
            self._unsubscribe = await mqtt.async_subscribe(
                self.hass, topic_pattern, self._mqtt_message_received, qos
            )
        except Exception as err:
            _LOGGER.error("Failed to subscribe to MQTT: %s", err)
            raise ConfigEntryNotReady("Failed to subscribe to MQTT topics") from err

        # Subscribe to gateway status topics
        status_topic_pattern = f"{topic_prefix}+/gw_status"
        _LOGGER.info(
            "Subscribing to gateway status topic: %s (QoS %d)",
            status_topic_pattern,
            qos,
        )

        try:
            await mqtt.async_subscribe(
                self.hass, status_topic_pattern, self._mqtt_status_received, qos
            )
        except Exception as err:
            _LOGGER.warning("Failed to subscribe to status topics: %s", err)

        # Start flush task
        self._flush_task = asyncio.create_task(self._flush_loop())

        _LOGGER.info("Ruuvi Gateway Bluetooth Proxy coordinator started")

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        # Unsubscribe from MQTT
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

        # Unregister all scanners
        for source, unregister_callback in self._scanner_unregister_callbacks.items():
            _LOGGER.debug("Unregistering scanner %s", source)
            unregister_callback()
        self._scanner_unregister_callbacks.clear()

        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task
            self._flush_task = None

        self._registered_scanners.clear()

        _LOGGER.info("Ruuvi Gateway Bluetooth Proxy coordinator shut down")

    @callback
    def _mqtt_status_received(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming gateway status message."""
        try:
            # Parse topic: ruuvi/<gateway_mac>/gw_status
            topic_parts = msg.topic.split("/")
            if len(topic_parts) < 3 or topic_parts[-1] != "gw_status":
                _LOGGER.debug("Invalid status topic format: %s", msg.topic)
                return

            gateway_mac = topic_parts[-2].upper()

            # Parse JSON payload
            try:
                payload = json.loads(msg.payload)
                state = payload.get("state", "").lower()
                is_online = state == "online"

                old_status = self._gateway_status.get(gateway_mac)
                self._gateway_status[gateway_mac] = is_online

                if old_status != is_online:
                    _LOGGER.info(
                        "Gateway %s is now %s",
                        gateway_mac,
                        "online" if is_online else "offline",
                    )

            except (json.JSONDecodeError, KeyError) as err:
                _LOGGER.debug("Invalid status JSON in topic %s: %s", msg.topic, err)

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error processing status message: %s", err)

    @callback
    def _mqtt_message_received(self, msg: mqtt.ReceiveMessage) -> None:
        """Handle incoming MQTT message."""
        self._stats[STAT_PACKETS_RECEIVED] += 1

        _LOGGER.debug("Received MQTT message on topic: %s", msg.topic)

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

            _LOGGER.debug(
                "Parsed topic - Gateway: %s, BLE Device: %s", gateway_mac, ble_mac
            )

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
            # Get epoch timestamp from gateway and convert to monotonic time
            epoch_timestamp = payload.get("ts", payload.get("gwts", int(time.time())))
            timestamp = epoch_timestamp - self._time_offset
            data_hex = payload.get("data", "")

            # Validate hex data
            if not data_hex or not isinstance(data_hex, str):
                _LOGGER.debug("Missing or invalid data field in topic %s", msg.topic)
                self._stats[STAT_INVALID_HEX] += 1
                self._stats[STAT_PACKETS_DROPPED] += 1
                return

            _LOGGER.debug(
                "Valid advertisement - RSSI: %d, Data length: %d", rssi, len(data_hex)
            )

            # Apply filters
            if not self._should_process(gateway_mac, ble_mac, rssi):
                _LOGGER.debug(
                    "Advertisement filtered out - Gateway: %s, BLE: %s, RSSI: %d",
                    gateway_mac,
                    ble_mac,
                    rssi,
                )
                return

            _LOGGER.debug("Advertisement passed filters, buffering...")

            # Create observation
            observation = BLEObservation(
                gateway_mac=gateway_mac,
                ble_mac=ble_mac,
                rssi=rssi,
                timestamp=timestamp,
                data_hex=data_hex,
            )

            # Buffer the observation in background
            task = asyncio.create_task(self._buffer_observation(observation))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

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

        # Per-gateway RSSI filter
        rssi_min = self.get_gateway_rssi_filter(gateway_mac)
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
            total_observations = sum(len(buf) for buf in self._buffers.values())
            if total_observations > 0:
                _LOGGER.debug(
                    "Flushing %d observations from %d gateways",
                    total_observations,
                    len(self._buffers),
                )

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
        # Use gateway MAC directly as source (like USB dongles do)
        source = gateway_mac

        if source not in self._registered_scanners:
            # Create device in device registry first (needed for scanner registration)
            self._create_gateway_device(gateway_mac)

            # Initialize RSSI filter with default if not set
            if gateway_mac not in self._gateway_rssi_filters:
                from .const import DEFAULT_RSSI_MIN

                self._gateway_rssi_filters[gateway_mac] = DEFAULT_RSSI_MIN

            # Register scanner with HA Bluetooth integration
            try:
                from habluetooth import BaseHaRemoteScanner
                from homeassistant.components.bluetooth import async_register_scanner

                # Create a remote scanner using the gateway MAC as source
                # This matches how USB dongles and ESPHome devices register
                scanner = BaseHaRemoteScanner(
                    source,  # MAC address as source (first argument!)
                    source,  # adapter - use same MAC as adapter ID
                    None,  # connector - no connection support for passive scanning
                    False,  # connectable - passive scanner only
                )

                # Get the gateway device ID for linking
                gateway_device_id = self._gateway_devices.get(gateway_mac)

                # Register scanner with the Bluetooth manager
                # This creates the Bluetooth scanner device in the bluetooth domain
                unregister_callback = async_register_scanner(
                    self.hass,
                    scanner,
                    connection_slots=0,  # Passive scanner, no connections
                    source_domain=DOMAIN,  # Our integration domain
                    source_model="Ruuvi Gateway",
                    source_config_entry_id=self.entry.entry_id,
                    source_device_id=gateway_device_id,  # Link to our gateway device
                )

                # Set up the scanner
                scanner.async_setup()

                self._scanner_unregister_callbacks[source] = unregister_callback
                self._registered_scanners.add(source)

                _LOGGER.info(
                    "Registered Bluetooth scanner for gateway %s with source %s (device_id: %s)",
                    gateway_mac,
                    source,
                    gateway_device_id,
                )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(
                    "Failed to register scanner for gateway %s: %s",
                    gateway_mac,
                    err,
                )
                # Continue even if scanner registration fails - mark as registered to avoid retries
                self._registered_scanners.add(source)

            # Notify discovery callbacks for new gateway
            for callback in self._gateway_discovered_callbacks:
                callback(gateway_mac)

    def _create_gateway_device(self, gateway_mac: str) -> None:
        """Create a device entry for a Ruuvi Gateway."""
        if not self._device_registry:
            _LOGGER.warning("Device registry not available")
            return

        # Skip if device already created
        if gateway_mac in self._gateway_devices:
            return

        try:
            # Create parent gateway device
            gateway_device = self._device_registry.async_get_or_create(
                config_entry_id=self.entry.entry_id,
                identifiers={(DOMAIN, gateway_mac)},
                connections={(dr.CONNECTION_NETWORK_MAC, gateway_mac)},
                name=f"Ruuvi Gateway {gateway_mac}",
                manufacturer="Ruuvi",
                model="Ruuvi Gateway",
            )

            # Note: The Bluetooth scanner device is created automatically by the
            # Bluetooth integration when we call async_register_scanner with
            # source_device_id pointing to this gateway device

            self._gateway_devices[gateway_mac] = gateway_device.id

            _LOGGER.info(
                "Created gateway device %s (device_id: %s)",
                gateway_mac,
                gateway_device.id,
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to create devices for gateway %s: %s", gateway_mac, err
            )

    async def _forward_to_bluetooth(self, observation: BLEObservation) -> None:
        """Forward a single observation to the Bluetooth backend."""
        try:
            _LOGGER.debug(
                "Forwarding advertisement - Gateway: %s, Device: %s, RSSI: %d",
                observation.gateway_mac,
                observation.ble_mac,
                observation.rssi,
            )

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

            # Create service info using gateway MAC as source (like USB dongles)
            source = observation.gateway_mac
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
                _LOGGER.debug(
                    "Successfully forwarded to Bluetooth - Device: %s, Source: %s",
                    observation.ble_mac,
                    source,
                )
            else:
                _LOGGER.warning("Bluetooth callback not available")

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Error forwarding to Bluetooth: %s", err)
            self._stats[STAT_PACKETS_DROPPED] += 1

    def register_gateway_discovered_callback(
        self, callback: Callable[[str], None]
    ) -> None:
        """Register a callback to be called when a new gateway is discovered."""
        self._gateway_discovered_callbacks.append(callback)

    def get_gateway_macs(self) -> list[str]:
        """Get list of all discovered gateway MACs."""
        return list(self._gateway_last_seen.keys())

    def get_gateway_rssi_filter(self, gateway_mac: str) -> int:
        """Get RSSI filter threshold for a gateway."""
        from .const import DEFAULT_RSSI_MIN

        return self._gateway_rssi_filters.get(gateway_mac, DEFAULT_RSSI_MIN)

    def set_gateway_rssi_filter(self, gateway_mac: str, rssi_min: int) -> None:
        """Set RSSI filter threshold for a gateway."""
        self._gateway_rssi_filters[gateway_mac] = rssi_min
        _LOGGER.debug("Set RSSI filter for gateway %s to %d", gateway_mac, rssi_min)

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
                    "source": mac,  # Use gateway MAC directly as source
                }
                for mac, last_seen in self._gateway_last_seen.items()
            },
            "registered_scanners": list(self._registered_scanners),
        }
