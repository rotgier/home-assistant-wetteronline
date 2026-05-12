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


def _parse_duration_minutes(raw: Any) -> tuple[int | None, int | None]:
    """Parse precipitation duration minutes — accepts 'X-Y' range or single 'X'.

    wo-cloud reports duration.minutes as a string. For low-prob hours it's
    "0-10"; for higher prob it can be a single value like "30" or "60".
    Returns (min, max) tuple; (None, None) when raw is missing/malformed.
    """
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s:
        return None, None
    if "-" in s:
        parts = s.split("-", 1)
        try:
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return None, None
    try:
        v = int(s)
        return v, v
    except ValueError:
        return None, None


def _parse_hourly_pv_extras(hour: dict[str, Any]) -> dict[str, Any]:
    """Extract PV-relevant fields from a wo-cloud hour entry.

    Returns flat dict ready for spread into hourly_forecast item. Keys:
    - precipitation_probability (int %, 0..100)
    - precipitation_amount_mm_min, _max (float | None — only when details present,
      typically when probability >= ~50%)
    - precipitation_duration_min_min, _max (int | None — duration in minutes
      within the hour; "X-Y" parsed as range, single "X" → min==max==X)
    - precipitation_type (str | None — "rain", "snow", etc.)
    - convection_probability (int %, 0..100)
    - visibility_meter (int | None)
    - smog_level (str | None — "none", "low", etc.)
    - dew_point_celsius (float | None)
    - air_pressure_hpa (int | None — wo-cloud returns string, cast to int)
    - wind_speed_kmh (int | None)
    - wind_direction_deg (int | None)
    """
    p = hour.get("precipitation", {}) or {}
    det = p.get("details", {}) or {}
    rain_mm = det.get("rainfall_amount", {}).get("millimeter", {}) or {}
    dur_min, dur_max = _parse_duration_minutes(det.get("duration", {}).get("minutes"))
    visibility = hour.get("visibility", {}) or {}
    wind = hour.get("wind", {}) or {}
    wind_kmh_value = (
        wind.get("speed", {}).get("kilometer_per_hour", {}).get("value")
    )
    try:
        wind_kmh = int(wind_kmh_value) if wind_kmh_value is not None else None
    except (ValueError, TypeError):
        wind_kmh = None
    try:
        pressure_hpa = int(hour.get("air_pressure", {}).get("hpa"))
    except (ValueError, TypeError):
        pressure_hpa = None
    return {
        "precipitation_probability": round(p.get("probability", 0) * 100),
        "precipitation_amount_mm_min": rain_mm.get("interval_begin"),
        "precipitation_amount_mm_max": rain_mm.get("interval_end"),
        "precipitation_duration_min_min": dur_min,
        "precipitation_duration_min_max": dur_max,
        "precipitation_type": p.get("type"),
        "convection_probability": round(hour.get("convection_probability", 0) * 100),
        "visibility_meter": visibility.get("meter"),
        "smog_level": hour.get("smog_level"),
        "dew_point_celsius": hour.get("dew_point", {}).get("celsius"),
        "air_pressure_hpa": pressure_hpa,
        "wind_speed_kmh": wind_kmh,
        "wind_direction_deg": wind.get("direction"),
    }


_NEXTHOUR_FIELDS: tuple[str, ...] = (
    "visibility_meter",
    "convection_probability",
    "precipitation_amount_mm_min",
    "precipitation_amount_mm_max",
    "precipitation_duration_min_min",
    "precipitation_duration_min_max",
)


def parse_nexthour_extras(hour: dict[str, Any]) -> dict[str, Any] | None:
    """Extract nexthour cache fields from a wo-cloud `hours[]` entry.

    `current` carries `precipitation.{probability,type}` only — never
    `precipitation.details.*` (rainfall amount, duration), and lacks
    `visibility` + `convection_probability` entirely. These fields live
    only in `hours[N]`. `hours[0]` is the upcoming round hour; storing it
    and promoting it to `current` at hour rollover lets us serve all six
    fields as current-hour sensors.

    Returns `{hour_iso, ...six fields}` or None when the entry is missing
    `date` (needed for cache promotion logic).

    Note: `details.*` is sometimes omitted by wo-cloud when probability is
    low (observed: present at prob=0.95, absent at prob=0.2). The defensive
    `.get()` chain in `_parse_hourly_pv_extras` yields None for those
    fields in that case — the sensor will simply report unknown.
    """
    hour_iso = hour.get("date")
    if not hour_iso:
        return None
    extras = _parse_hourly_pv_extras(hour)
    return {"hour_iso": hour_iso} | {k: extras.get(k) for k in _NEXTHOUR_FIELDS}


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
    next_hour_raw: dict[str, Any] | None = None


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
        # Reuse hourly extras parser — `current` shares most fields with `hours[N]`.
        # `current` adds: solar_elevation, air_pressure_tendency_category,
        # weather_condition_image (no convection_probability / visibility).
        current_extras = _parse_hourly_pv_extras(current)
        # Drop hour-only fields that current doesn't carry (avoid misleading 0s).
        current_extras.pop("convection_probability", None)
        current_extras.pop("visibility_meter", None)
        current_observations = {
            "temperature": current.get("air_temperature", {}).get("celsius"),
            "apparentTemperature": current.get("apparent_temperature", {}).get("celsius"),
            "humidity": round(current.get("humidity", 0) * 100)
            if current.get("humidity") is not None
            else None,
            "symbol": current_symbol,
            "condition_custom": SYMBOLTEXT_CONDITION_CUSTOM_MAP.get(
                current_symbol, current_symbol
            ),
            # Current-only extras (not present in hour entries).
            "solar_elevation": current.get("solar_elevation"),
            "air_pressure_tendency_category": current.get(
                "air_pressure_tendency_category"
            ),
            "weather_condition_image": current.get("weather_condition_image"),
            **current_extras,
        }

        hours = shortcast.get("hours", [])
        next_hour_raw = parse_nexthour_extras(hours[0]) if hours else None

        hourly_forecast = []
        for hour in hours:
            hourly_forecast.append({
                "datetime": datetime.fromisoformat(hour["date"]),
                "temperature": hour["air_temperature"]["celsius"],
                "apparentTemperature": hour["apparent_temperature"]["celsius"],
                "humidity": round(hour["humidity"] * 100),
                "symbol": hour.get("symbol", ""),
                "symbolText": hour.get("symbol", ""),
                **_parse_hourly_pv_extras(hour),
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
            next_hour_raw=next_hour_raw,
        )
