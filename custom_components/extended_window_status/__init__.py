import logging
from typing import Any, Dict
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: Dict) -> bool:
    """Set up the Extended window status integration."""
    _LOGGER.debug("Setting up Extended window status")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: Dict) -> bool:
    """Set up extended window status from a config entry."""
    _LOGGER.debug(f"Setting up config entry: {entry.entry_id}")
    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True