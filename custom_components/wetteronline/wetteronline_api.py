"""API for fetching WetterOnline data via wo-cloud API."""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Final
from zoneinfo import ZoneInfo

from aiohttp import ClientSession

from .const import SYMBOLTEXT_CONDITION_CUSTOM_MAP

API_BASE: Final = "https://api-web.wo-cloud.com"
API_KEY: Final = "d293ZWI6QzhMNFRINmVUbkRoVWFqYg=="
TIMEZONE: Final = ZoneInfo("Europe/Warsaw")

_LOGGER = logging.getLogger(__name__)


@dataclass
class WetterOnlineLocationParams:
    """Location parameters for wo-cloud API."""

    location_id: str
    latitude: float
    longitude: float
    grid_latitude: float
    grid_longitude: float
    astro_latitude: float
    astro_longitude: float
    altitude: int


@dataclass
class WetterOnlineData:
    """Data from WetterOnline."""

    current_observations: dict[str, Any]
    daily_forecast: list[dict[str, Any]]
    hourly_forecast: list[dict[str, Any]]


class WetterOnline:
    """Main class to perform WetterOnline requests via wo-cloud API."""

    def __init__(self, session: ClientSession, location: WetterOnlineLocationParams) -> None:  # noqa: D107
        self._session = session
        self._location = location
        self.complete_url = f"https://www.wetteronline.de/wetter/{location.location_id}"

    async def _get_release_version(self) -> str:
        url = f"{API_BASE}/blending/release/latest/v1?c={API_KEY}"
        async with self._session.get(url) as resp:
            data = await resp.json()
            return data["release"]

    async def _get_shortcast(self, release: str) -> dict:
        loc = self._location
        url = (
            f"{API_BASE}/blending/shortcast/v1?c={API_KEY}"
            f"&language=de&timezone=Europe/Warsaw"
            f"&location_id={loc.location_id}"
            f"&latitude={loc.latitude}&longitude={loc.longitude}"
            f"&astro_latitude={loc.astro_latitude}&astro_longitude={loc.astro_longitude}"
            f"&altitude={loc.altitude}"
            f"&grid_latitude={loc.grid_latitude}&grid_longitude={loc.grid_longitude}"
            f"&release_version={release}"
        )
        async with self._session.get(url) as resp:
            return await resp.json()

    async def _get_forecast(self, release: str) -> dict:
        loc = self._location
        url = (
            f"{API_BASE}/blending/forecast/v1?c={API_KEY}"
            f"&timezone=Europe/Warsaw"
            f"&location_id={loc.location_id}"
            f"&grid_latitude={loc.grid_latitude}&grid_longitude={loc.grid_longitude}"
            f"&release_version={release}"
        )
        async with self._session.get(url) as resp:
            return await resp.json()

    async def async_get_weather(self) -> WetterOnlineData:
        """Fetch data from WetterOnline wo-cloud API."""
        release = await self._get_release_version()
        shortcast = await self._get_shortcast(release)
        forecast = await self._get_forecast(release)

        current = shortcast.get("current", {})
        current_symbol = current.get("symbol", "")
        current_observations = {
            "temperature": current.get("air_temperature", {}).get("celsius"),
            "symbol": current_symbol,
            "condition_custom": SYMBOLTEXT_CONDITION_CUSTOM_MAP.get(
                current_symbol, current_symbol
            ),
        }

        hourly_forecast = []
        for hour in shortcast.get("hours", []):
            hourly_forecast.append({
                "datetime": datetime.fromisoformat(hour["date"]),
                "temperature": hour["air_temperature"]["celsius"],
                "apparentTemperature": hour["apparent_temperature"]["celsius"],
                "humidity": round(hour["humidity"] * 100),
                "symbol": hour.get("symbol", ""),
                "symbolText": hour.get("symbol", ""),
            })

        daily_forecast = []
        for day in forecast.get("days", []):
            daily_forecast.append({
                "datetime": datetime.fromisoformat(day["date"]),
                "maxTemperature": day["air_temperature"]["max"]["celsius"],
                "minTemperature": day["air_temperature"]["min"]["celsius"],
                "precipitationProbability": round(day["precipitation"]["probability"] * 100),
            })

        return WetterOnlineData(
            current_observations=current_observations,
            daily_forecast=daily_forecast,
            hourly_forecast=hourly_forecast,
        )
