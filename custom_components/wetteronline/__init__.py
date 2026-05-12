"""The WetterOnline component."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store

from .const import CONF_URL_WETTERONLINE, DOMAIN, UPDATE_INTERVAL_WETTERONLINE
from .coordinator import WeatherOnlineDataUpdateCoordinator
from .wetteronline_api import WetterOnline, WetterOnlineLocationParams

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.WEATHER]

NEXTHOUR_STORE_KEY = f"{DOMAIN}_nexthour_cache"
NEXTHOUR_STORE_VERSION = 1


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

    nexthour_store: Store = Store(hass, NEXTHOUR_STORE_VERSION, NEXTHOUR_STORE_KEY)
    coordinator = WeatherOnlineDataUpdateCoordinator(
        hass, wetteronline, name, UPDATE_INTERVAL_WETTERONLINE, nexthour_store
    )

    await coordinator.async_restore_nexthour_cache()
    await coordinator.async_config_entry_first_refresh()

    # Force an extra coordinator refresh at :59:30 of every hour. The regular
    # 5-min poll already feeds `cache.next`; the :59:30 fetch ensures the
    # freshest possible data right before the hour rolls over and `cache.next`
    # is promoted to `cache.current`.
    @callback
    def _hourly_refresh(_now) -> None:
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(
        async_track_time_change(hass, _hourly_refresh, minute=59, second=30)
    )

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WetterOnlineConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
