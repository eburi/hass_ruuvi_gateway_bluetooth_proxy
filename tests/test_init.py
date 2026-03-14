"""Test init module."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.ruuvi_gateway_bt_proxy import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.ruuvi_gateway_bt_proxy.const import DOMAIN


async def test_setup_entry_success(hass: HomeAssistant, mock_config_entry):
    """Test successful setup of config entry."""
    with (
        patch(
            "custom_components.ruuvi_gateway_bt_proxy.coordinator.RuuviGatewayCoordinator.async_setup",
            return_value=None,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
    ):
        assert await async_setup_entry(hass, mock_config_entry)
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_failure(hass: HomeAssistant, mock_config_entry):
    """Test failed setup of config entry."""
    with (
        patch(
            "custom_components.ruuvi_gateway_bt_proxy.coordinator.RuuviGatewayCoordinator.async_setup",
            side_effect=Exception("Test error"),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
    ):
        assert not await async_setup_entry(hass, mock_config_entry)


async def test_unload_entry(hass: HomeAssistant, mock_config_entry):
    """Test unload of config entry."""
    # Setup first
    with (
        patch(
            "custom_components.ruuvi_gateway_bt_proxy.coordinator.RuuviGatewayCoordinator.async_setup",
            return_value=None,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=None),
        ),
    ):
        await async_setup_entry(hass, mock_config_entry)

    # Mock the shutdown
    with (
        patch(
            "custom_components.ruuvi_gateway_bt_proxy.coordinator.RuuviGatewayCoordinator.async_shutdown",
            return_value=None,
        ),
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            AsyncMock(return_value=True),
        ),
    ):
        assert await async_unload_entry(hass, mock_config_entry)
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
