"""The Ruuvi Gateway Bluetooth Proxy integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DEBUG_ENTITY, DOMAIN
from .coordinator import RuuviGatewayCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ruuvi Gateway Bluetooth Proxy from a config entry."""
    # Merge entry data and options
    config = {**entry.data, **entry.options}
    
    # Create coordinator
    coordinator = RuuviGatewayCoordinator(hass, config)
    
    try:
        await coordinator.async_setup()
    except Exception as err:
        _LOGGER.error("Failed to set up Ruuvi Gateway Bluetooth Proxy: %s", err)
        return False
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up platforms if debug entity is enabled
    if config.get(CONF_DEBUG_ENTITY, False):
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    _LOGGER.info("Ruuvi Gateway Bluetooth Proxy integration set up successfully")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    config = {**entry.data, **entry.options}
    if config.get(CONF_DEBUG_ENTITY, False):
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_ok = True
    
    if unload_ok:
        # Shut down coordinator
        coordinator: RuuviGatewayCoordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()
        
        # Remove coordinator from hass.data
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
