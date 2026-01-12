"""Tests for config flow."""

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ruuvi_gateway_bt_proxy.config_flow import (
    normalize_topic_prefix,
    validate_mac_list,
)
from custom_components.ruuvi_gateway_bt_proxy.const import (
    CONF_BATCH_WINDOW_MS,
    CONF_DEBUG_ENTITY,
    CONF_DEVICE_WHITELIST,
    CONF_GATEWAY_WHITELIST,
    CONF_QOS,
    CONF_RSSI_MIN,
    CONF_TOPIC_PREFIX,
    DOMAIN,
)


def test_normalize_topic_prefix():
    """Test topic prefix normalization."""
    assert normalize_topic_prefix("ruuvi") == "ruuvi/"
    assert normalize_topic_prefix("ruuvi/") == "ruuvi/"
    assert normalize_topic_prefix("ruuvi/ ") == "ruuvi/"
    assert normalize_topic_prefix(" custom/path ") == "custom/path/"


def test_validate_mac_list():
    """Test MAC address list validation."""
    # Valid lists
    assert validate_mac_list("") == []
    assert validate_mac_list("AA:BB:CC:DD:EE:FF") == ["AA:BB:CC:DD:EE:FF"]
    assert validate_mac_list("aa:bb:cc:dd:ee:ff") == ["AA:BB:CC:DD:EE:FF"]
    assert validate_mac_list("AA:BB:CC:DD:EE:FF, 11:22:33:44:55:66") == [
        "AA:BB:CC:DD:EE:FF",
        "11:22:33:44:55:66",
    ]

    # Invalid MAC should raise
    with pytest.raises(Exception):
        validate_mac_list("INVALID")


async def test_user_flow_success(hass: HomeAssistant):
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_TOPIC_PREFIX: "ruuvi/",
            CONF_QOS: 0,
            CONF_GATEWAY_WHITELIST: "",
            CONF_DEVICE_WHITELIST: "",
            CONF_RSSI_MIN: -80,
            CONF_BATCH_WINDOW_MS: 250,
            CONF_DEBUG_ENTITY: False,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ruuvi Gateway BT Proxy"
    assert result["data"][CONF_TOPIC_PREFIX] == "ruuvi/"
    assert result["data"][CONF_RSSI_MIN] == -80


async def test_user_flow_with_whitelist(hass: HomeAssistant):
    """Test user flow with MAC whitelists."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_TOPIC_PREFIX: "custom",
            CONF_QOS: 1,
            CONF_GATEWAY_WHITELIST: "AA:BB:CC:DD:EE:FF",
            CONF_DEVICE_WHITELIST: "11:22:33:44:55:66, 77:88:99:AA:BB:CC",
            CONF_RSSI_MIN: -60,
            CONF_BATCH_WINDOW_MS: 500,
            CONF_DEBUG_ENTITY: True,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_TOPIC_PREFIX] == "custom/"
    assert result["data"][CONF_GATEWAY_WHITELIST] == ["AA:BB:CC:DD:EE:FF"]
    assert result["data"][CONF_DEVICE_WHITELIST] == [
        "11:22:33:44:55:66",
        "77:88:99:AA:BB:CC",
    ]
