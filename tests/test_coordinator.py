"""Tests for coordinator."""

import json

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ruuvi_gateway_bt_proxy.const import (
    CONF_BATCH_WINDOW_MS,
    CONF_DEVICE_WHITELIST,
    CONF_GATEWAY_WHITELIST,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
    STAT_FILTERED_DEVICE,
    STAT_FILTERED_GATEWAY,
    STAT_FILTERED_RSSI,
)
from custom_components.ruuvi_gateway_bt_proxy.coordinator import (
    BLEObservation,
    RuuviGatewayCoordinator,
)

# Note: Scanner registration tests require mocking HomeAssistant's Bluetooth integration
# The scanner uses BaseHaRemoteScanner(source, adapter, connector, connectable)
# and async_register_scanner(hass, scanner, connection_slots, source_domain, source_model,
#                            source_config_entry_id, source_device_id)
# These are tested via integration tests with the full HA stack.


@pytest.fixture
def mock_config():
    """Return mock configuration."""
    return {
        CONF_TOPIC_PREFIX: "ruuvi/",
        CONF_QOS: 0,
        CONF_GATEWAY_WHITELIST: [],
        CONF_DEVICE_WHITELIST: [],
        CONF_BATCH_WINDOW_MS: 250,
    }


def test_topic_parsing():
    """Test MQTT topic parsing."""
    # Valid topic
    topic = "ruuvi/C1:05:28:BF:A7:E7/6B:EF:59:3C:53:D9"
    parts = topic.split("/")
    assert len(parts) == 3
    assert parts[-2] == "C1:05:28:BF:A7:E7"
    assert parts[-1] == "6B:EF:59:3C:53:D9"


def test_payload_parsing():
    """Test MQTT payload parsing."""
    payload = '{"gw_mac":"C1:05:28:BF:A7:E7","rssi":-49,"aoa":[],"gwts":1768151705,"ts":1768151705,"data":"07FF4C0012020001","coords":""}'

    data = json.loads(payload)

    assert data["gw_mac"] == "C1:05:28:BF:A7:E7"
    assert data["rssi"] == -49
    assert data["ts"] == 1768151705
    assert data["data"] == "07FF4C0012020001"


def test_ble_observation_creation():
    """Test BLEObservation dataclass."""
    obs = BLEObservation(
        gateway_mac="AA:BB:CC:DD:EE:FF",
        ble_mac="11:22:33:44:55:66",
        rssi=-60,
        timestamp=1234567890,
        data_hex="02010611FF990405",
    )

    assert obs.gateway_mac == "AA:BB:CC:DD:EE:FF"
    assert obs.ble_mac == "11:22:33:44:55:66"
    assert obs.rssi == -60


async def test_coordinator_filtering_gateway(
    hass: HomeAssistant, mock_config, mock_config_entry
):
    """Test coordinator gateway whitelist filtering."""
    mock_config[CONF_GATEWAY_WHITELIST] = ["AA:BB:CC:DD:EE:FF"]

    coordinator = RuuviGatewayCoordinator(hass, mock_config_entry, mock_config)

    # Should pass
    assert coordinator._should_process("AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66", -50)

    # Should fail
    assert not coordinator._should_process(
        "FF:EE:DD:CC:BB:AA", "11:22:33:44:55:66", -50
    )
    assert coordinator._stats[STAT_FILTERED_GATEWAY] == 1


async def test_coordinator_filtering_device(
    hass: HomeAssistant, mock_config, mock_config_entry
):
    """Test coordinator device whitelist filtering."""
    mock_config[CONF_DEVICE_WHITELIST] = ["11:22:33:44:55:66"]

    coordinator = RuuviGatewayCoordinator(hass, mock_config_entry, mock_config)

    # Should pass
    assert coordinator._should_process("AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66", -50)

    # Should fail
    assert not coordinator._should_process(
        "AA:BB:CC:DD:EE:FF", "77:88:99:AA:BB:CC", -50
    )
    assert coordinator._stats[STAT_FILTERED_DEVICE] == 1


async def test_coordinator_filtering_rssi(
    hass: HomeAssistant, mock_config, mock_config_entry
):
    """Test coordinator RSSI filtering."""
    coordinator = RuuviGatewayCoordinator(hass, mock_config_entry, mock_config)

    # Set RSSI filter for test gateway
    coordinator.set_gateway_rssi_filter("AA:BB:CC:DD:EE:FF", -60)

    # Should pass
    assert coordinator._should_process("AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66", -50)

    # Should fail
    assert not coordinator._should_process(
        "AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66", -70
    )
    assert coordinator._stats[STAT_FILTERED_RSSI] == 1


async def test_coordinator_coalescing(
    hass: HomeAssistant, mock_config, mock_config_entry
):
    """Test observation coalescing by RSSI."""
    coordinator = RuuviGatewayCoordinator(hass, mock_config_entry, mock_config)

    obs1 = BLEObservation(
        gateway_mac="AA:BB:CC:DD:EE:FF",
        ble_mac="11:22:33:44:55:66",
        rssi=-60,
        timestamp=1000,
        data_hex="0201060506",
    )

    obs2 = BLEObservation(
        gateway_mac="AA:BB:CC:DD:EE:FF",
        ble_mac="11:22:33:44:55:66",
        rssi=-50,  # Higher RSSI
        timestamp=1001,
        data_hex="020106050607",
    )

    # Buffer both
    await coordinator._buffer_observation(obs1)
    await coordinator._buffer_observation(obs2)

    # Should keep obs2 (higher RSSI)
    buffered = coordinator._buffers["AA:BB:CC:DD:EE:FF"]["11:22:33:44:55:66"]
    assert buffered.rssi == -50
    assert buffered.data_hex == "020106050607"
