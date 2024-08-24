"""The WetterOnline component."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_URL_WETTERONLINE, UPDATE_INTERVAL_WETTERONLINE
from .coordinator import WeatherOnlineDataUpdateCoordinator
from .wetteronline_api import WetterOnline

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.WEATHER]


type WetterOnlineConfigEntry = ConfigEntry[WeatherOnlineDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: WetterOnlineConfigEntry
) -> bool:
    """Set up WetterOnline as config entry."""
    url: str = entry.data[CONF_URL_WETTERONLINE]
    name: str = entry.data[CONF_NAME]

    _LOGGER.debug("Using url: %s", url)

    websession = async_get_clientsession(hass)
    wetteronline = WetterOnline(websession, url)

    coordinator = WeatherOnlineDataUpdateCoordinator(
        hass, wetteronline, name, UPDATE_INTERVAL_WETTERONLINE
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WetterOnlineConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
