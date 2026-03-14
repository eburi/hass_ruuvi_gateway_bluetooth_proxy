"""Unit tests for Ruuvi Gateway Bluetooth Proxy integration."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    return MockConfigEntry(
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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations from this repository in tests."""
    yield
