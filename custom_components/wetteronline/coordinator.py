"""The WetterOnline coordinator."""

from asyncio import timeout
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .hourly_forecast import HourlyForecastInput
from .wetteronline_api import WetterOnline, WetterOnlineData

_LOGGER = logging.getLogger(__name__)

# Fired on the bus once per ~5-min refresh cycle so external consumers (e.g.
# smart_rce garden rain observation) get a guaranteed heartbeat: UPDATED on a
# successful fetch, UPDATE_FAILED otherwise. Together they mean "one signal
# every cycle, always", regardless of whether the data changed.
EVENT_WEATHER_UPDATED = f"{DOMAIN}_weather_updated"
EVENT_WEATHER_UPDATE_FAILED = f"{DOMAIN}_weather_update_failed"

NEXTHOUR_CACHE_VERSION = 1
NEXTHOUR_EMPTY_CACHE: dict[str, Any] = {
    "version": NEXTHOUR_CACHE_VERSION,
    "current": None,
    "next": None,
}


class WeatherOnlineDataUpdateCoordinator(DataUpdateCoordinator[WetterOnlineData]):
    """Class to manage fetching WetterOnline data."""

    def __init__(
        self,
        hass: HomeAssistant,
        wetteronline: WetterOnline,
        name: str,
        nexthour_store: Store,
    ) -> None:
        """Initialize.

        `update_interval=None` disables the internal scheduler — refreshes
        are driven externally by `async_track_time_change(minute="*/5",
        second=0)` registered in `__init__.py`. Aligning to round 5-min
        marks keeps sensor state-change timestamps clean and matches the
        forecast/nowcast bucket boundaries.
        """
        self.wetteronline = wetteronline
        self.nexthour_store = nexthour_store
        # Sliding-window cache for the visibility/convection sensors.
        # `current` holds the data for the current clock hour, `next` for
        # the upcoming one. On rollover, `next` is promoted to `current`.
        self.nexthour_cache: dict[str, Any] = dict(NEXTHOUR_EMPTY_CACHE)
        # Local timestamp of the most recent successful fetch. Surfaced on
        # the synthesized current-hour forecast entry so consumers can tell
        # how fresh the coordinator-wide data is (separate from per-bucket
        # `cache.<current|next>.fetched_at` which only covers the cached
        # hour-forecast slice).
        self.last_fetched_at: datetime | None = None

        if TYPE_CHECKING:
            assert name is not None

        self.device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, name)},
            manufacturer="wetteronline.de",
            name=name,
            configuration_url=wetteronline.complete_url,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=None,
        )

    @property
    def forecast_input(self) -> HourlyForecastInput | None:
        """Snapshot of state needed by `hourly_forecast.build_hourly_forecast`.

        Glue layer: infra → domain. Entities call this to obtain a frozen DTO
        and pass it to the pure-domain builder. Returns None until the first
        successful fetch populates `self.data`.
        """
        data = self.data
        if data is None:
            return None
        return HourlyForecastInput(
            hourly_forecast=data.hourly_forecast,
            current_observations=data.current_observations,
            nexthour_cache_current=(self.nexthour_cache or {}).get("current"),
            last_fetched_at=self.last_fetched_at,
            nowcast_items=data.nowcast_items,
        )

    async def async_restore_nexthour_cache(self) -> None:
        """Load the persisted nexthour cache from disk, if present."""
        stored = await self.nexthour_store.async_load()
        if isinstance(stored, dict) and stored.get("version") == NEXTHOUR_CACHE_VERSION:
            self.nexthour_cache = stored

    async def _async_update_data(self) -> WetterOnlineData:
        """Update data via library."""
        try:
            async with timeout(10):
                result = await self.wetteronline.async_get_weather()
        except Exception as error:
            _LOGGER.exception("Update failed")
            self.hass.bus.async_fire(EVENT_WEATHER_UPDATE_FAILED)
            raise UpdateFailed(error) from error

        self.last_fetched_at = dt_util.now()
        self._update_nexthour_cache(result.next_hour_raw)
        await self.nexthour_store.async_save(self.nexthour_cache)
        self.hass.bus.async_fire(EVENT_WEATHER_UPDATED)
        return result

    def _update_nexthour_cache(self, new_next: dict[str, Any] | None) -> None:
        """Promote `next → current` on hour rollover, refresh `next` otherwise.

        Stamps `fetched_at` on the new `next` entry so consumers can tell how
        fresh the cached values are. The stamp travels with the data when it
        is promoted to `current`, so the timestamp on `current` reflects the
        moment its values were last fetched from wo-cloud — typically the
        last :55 refresh before the clock-hour rollover.
        """
        if not new_next or not new_next.get("hour_iso"):
            return
        stamped_next = {**new_next, "fetched_at": dt_util.now().isoformat()}
        current_next = self.nexthour_cache.get("next")
        if current_next and current_next.get("hour_iso") == new_next["hour_iso"]:
            # Same upcoming hour — refresh values, forecast precision improves
            # as the hour approaches.
            self.nexthour_cache["next"] = stamped_next
        else:
            # Hour boundary crossed since last fetch — what was "next" is now
            # the current hour's data; this fetch's hours[0] becomes the new
            # "next".
            self.nexthour_cache["current"] = current_next
            self.nexthour_cache["next"] = stamped_next
