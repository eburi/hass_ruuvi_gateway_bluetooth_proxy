"""Config flow for Ruuvi Gateway Bluetooth Proxy integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_BATCH_WINDOW_MS,
    CONF_DEBUG_ENTITY,
    CONF_DEVICE_WHITELIST,
    CONF_GATEWAY_WHITELIST,
    CONF_QOS,
    CONF_TOPIC_PREFIX,
    DEFAULT_BATCH_WINDOW_MS,
    DEFAULT_QOS,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def normalize_topic_prefix(prefix: str) -> str:
    """Normalize topic prefix to ensure it ends with /."""
    prefix = prefix.strip()
    if not prefix.endswith("/"):
        prefix += "/"
    return prefix


def validate_mac_list(mac_list: str) -> list[str]:
    """Validate and parse comma-separated MAC address list."""
    if not mac_list.strip():
        return []
    macs = [mac.strip().upper() for mac in mac_list.split(",")]
    # Basic validation - check format
    for mac in macs:
        if not all(c in "0123456789ABCDEF:" for c in mac):
            raise vol.Invalid(f"Invalid MAC address format: {mac}")
    return macs


class RuuviGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ruuvi Gateway Bluetooth Proxy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Normalize topic prefix
                user_input[CONF_TOPIC_PREFIX] = normalize_topic_prefix(
                    user_input[CONF_TOPIC_PREFIX]
                )

                # Validate and parse whitelist fields
                if CONF_GATEWAY_WHITELIST in user_input:
                    user_input[CONF_GATEWAY_WHITELIST] = validate_mac_list(
                        user_input[CONF_GATEWAY_WHITELIST]
                    )

                if CONF_DEVICE_WHITELIST in user_input:
                    user_input[CONF_DEVICE_WHITELIST] = validate_mac_list(
                        user_input[CONF_DEVICE_WHITELIST]
                    )

                # Create entry
                return self.async_create_entry(
                    title="Ruuvi Gateway BT Proxy", data=user_input
                )
            except vol.Invalid as err:
                _LOGGER.error("Validation error: %s", err)
                errors["base"] = "invalid_mac"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX
                ): cv.string,
                vol.Optional(CONF_QOS, default=DEFAULT_QOS): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=2)
                ),
                vol.Optional(CONF_GATEWAY_WHITELIST, default=""): cv.string,
                vol.Optional(CONF_DEVICE_WHITELIST, default=""): cv.string,
                vol.Optional(
                    CONF_BATCH_WINDOW_MS, default=DEFAULT_BATCH_WINDOW_MS
                ): vol.All(vol.Coerce(int), vol.Range(min=50, max=5000)),
                vol.Optional(CONF_DEBUG_ENTITY, default=False): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return RuuviGatewayOptionsFlow(config_entry)


class RuuviGatewayOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Ruuvi Gateway Bluetooth Proxy."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Normalize topic prefix
                user_input[CONF_TOPIC_PREFIX] = normalize_topic_prefix(
                    user_input[CONF_TOPIC_PREFIX]
                )

                # Validate and parse whitelist fields
                if CONF_GATEWAY_WHITELIST in user_input:
                    user_input[CONF_GATEWAY_WHITELIST] = validate_mac_list(
                        user_input[CONF_GATEWAY_WHITELIST]
                    )

                if CONF_DEVICE_WHITELIST in user_input:
                    user_input[CONF_DEVICE_WHITELIST] = validate_mac_list(
                        user_input[CONF_DEVICE_WHITELIST]
                    )

                return self.async_create_entry(title="", data=user_input)
            except vol.Invalid as err:
                _LOGGER.error("Validation error: %s", err)
                errors["base"] = "invalid_mac"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Get current values from config entry
        current_data = {**self.config_entry.data, **self.config_entry.options}

        # Convert list to comma-separated string for display
        gateway_whitelist = current_data.get(CONF_GATEWAY_WHITELIST, [])
        device_whitelist = current_data.get(CONF_DEVICE_WHITELIST, [])

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TOPIC_PREFIX,
                    default=current_data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX),
                ): cv.string,
                vol.Optional(
                    CONF_QOS, default=current_data.get(CONF_QOS, DEFAULT_QOS)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=2)),
                vol.Optional(
                    CONF_GATEWAY_WHITELIST,
                    default=", ".join(gateway_whitelist)
                    if isinstance(gateway_whitelist, list)
                    else gateway_whitelist,
                ): cv.string,
                vol.Optional(
                    CONF_DEVICE_WHITELIST,
                    default=", ".join(device_whitelist)
                    if isinstance(device_whitelist, list)
                    else device_whitelist,
                ): cv.string,
                vol.Optional(
                    CONF_BATCH_WINDOW_MS,
                    default=current_data.get(
                        CONF_BATCH_WINDOW_MS, DEFAULT_BATCH_WINDOW_MS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=50, max=5000)),
                vol.Optional(
                    CONF_DEBUG_ENTITY,
                    default=current_data.get(CONF_DEBUG_ENTITY, False),
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
