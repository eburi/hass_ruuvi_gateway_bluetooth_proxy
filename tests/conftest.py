"""Unit tests for Ruuvi Gateway Bluetooth Proxy integration."""

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.ruuvi_gateway_bt_proxy.const import (
    CONF_BATCH_WINDOW_MS,
    CONF_DEVICE_WHITELIST,
    CONF_GATEWAY_WHITELIST,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
    DEFAULT_BATCH_WINDOW_MS,
    DEFAULT_QOS,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Ruuvi Gateway BT Proxy",
        data={
            CONF_TOPIC_PREFIX: DEFAULT_TOPIC_PREFIX,
            CONF_QOS: DEFAULT_QOS,
            CONF_GATEWAY_WHITELIST: [],
            CONF_DEVICE_WHITELIST: [],
            CONF_BATCH_WINDOW_MS: DEFAULT_BATCH_WINDOW_MS,
        },
        source="user",
        entry_id="test_entry_id",
        options={},
    )
