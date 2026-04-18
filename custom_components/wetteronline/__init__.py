"""The WetterOnline component."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_URL_WETTERONLINE, UPDATE_INTERVAL_WETTERONLINE
from .coordinator import WeatherOnlineDataUpdateCoordinator
from .wetteronline_api import WetterOnline, WetterOnlineLocationParams

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.WEATHER]


type WetterOnlineConfigEntry = ConfigEntry[WeatherOnlineDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: WetterOnlineConfigEntry
) -> bool:
    """Set up WetterOnline as config entry."""
    name: str = entry.data[CONF_NAME]

    # TODO: extract location params from config entry or HTML page
    location = WetterOnlineLocationParams(
        location_id="12566",
        latitude=50.1225,
        longitude=19.71,
        grid_latitude=50.10,
        grid_longitude=19.76,
        astro_latitude=50.10,
        astro_longitude=19.68,
        altitude=250,
    )

    _LOGGER.debug("Using location_id: %s", location.location_id)

    websession = async_get_clientsession(hass)
    wetteronline = WetterOnline(websession, location)

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
