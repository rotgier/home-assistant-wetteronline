"""The WetterOnline coordinator."""

from asyncio import timeout
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from .wetteronline_api import WetterOnline, WetterOnlineData
from aiohttp.client_exceptions import ClientConnectorError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

# EXCEPTIONS = (ApiError, ClientConnectorError, InvalidApiKeyError, RequestsExceededError)

_LOGGER = logging.getLogger(__name__)


class WeatherOnlineDataUpdateCoordinator(DataUpdateCoordinator[WetterOnlineData]):
    """Class to manage fetching WetterOnline data."""

    def __init__(
        self,
        hass: HomeAssistant,
        wetteronline: WetterOnline,
        name: str,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.wetteronline = wetteronline
        # self.location_key = wetteronline.location_key

        # if TYPE_CHECKING:
        #    assert self.location_key is not None

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
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with timeout(10):
                result = await self.wetteronline.async_get_weather()
        except Exception as error:
            raise UpdateFailed(error) from error

        return result
