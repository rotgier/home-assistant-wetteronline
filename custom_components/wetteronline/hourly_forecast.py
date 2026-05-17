"""Hourly forecast domain — pure builder over WetterOnline data.

Combines the coordinator's raw `hourly_forecast` list with a synthesized
current-hour entry assembled from current observations, the nexthour cache,
and the 15-min nowcast items. The synthesized entry fills the gap left by
wo-cloud's `hours[]`, which typically starts at the next round hour — without
it, the forecast list skips the hour we are actually in (the most decision-
relevant slot for "should I run X now").

Layering: this module is pure domain — it accepts a frozen `HourlyForecastInput`
DTO and returns a list of `Forecast` dicts. It does not import the coordinator
or any other infrastructure; instead, the coordinator builds the DTO from its
state and the entities pass it to `build_hourly_forecast`.

Used by:
- `WetterOnlineEntity._async_forecast_hourly`
- `WetterOnlineForecastForTodaySensor` / `WetterOnlineForecastForTomorrowSensor`
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_APPARENT_TEMP,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    Forecast,
)

from .const import (
    ATTR_CONDITION_UNKNOWN,
    ATTR_FORECAST_CONDITION_CUSTOM,
    ATTR_FORECAST_CONDITION_SYMBOL,
    ATTR_FORECAST_CONDITION_SYMBOLTEXT,
    ATTR_FORECAST_SYMBOL,
    ATTR_FORECAST_SYMBOLTEXT,
    SYMBOLTEXT_CONDITION_CUSTOM_MAP,
    SYMBOLTEXT_CONDITION_MAP,
)


@dataclass(frozen=True)
class HourlyForecastInput:
    """Snapshot of coordinator state needed to build the hourly forecast.

    Frozen DTO — domain accepts this and never sees coordinator/HA infra.
    Built by `WeatherOnlineDataUpdateCoordinator.forecast_input` property.
    """

    hourly_forecast: list[dict[str, Any]]
    current_observations: dict[str, Any] | None
    nexthour_cache_current: dict[str, Any] | None
    last_fetched_at: datetime | None
    nowcast_items: list[dict[str, Any]]


def build_hourly_forecast(
    inp: HourlyForecastInput, now: datetime
) -> list[Forecast]:
    """Return forecast list with synthesized current-hour entry prepended.

    Edge case: in a ~5 min window right after a clock hour rolls over and
    before the next coordinator fetch, wo-cloud's `hours[0]` may still
    report the now-current round hour. In that window the synthesized entry
    and `hours[0]` would target the same hour — replace `hours[0]` with the
    synthesized entry (strictly richer data: live obs + cache + nowcast).
    """
    items = [_hourly_forecast_item(item) for item in inp.hourly_forecast]
    synthesized = _synthesize_current_hour(inp, now)
    if not synthesized:
        return items
    if items and _same_hour(
        items[0][ATTR_FORECAST_TIME], synthesized[ATTR_FORECAST_TIME]
    ):
        return [synthesized, *items[1:]]
    return [synthesized, *items]


def _hourly_forecast_item(item: dict[str, Any]) -> Forecast:
    symbol = item["symbol"]
    symbol_text = item["symbolText"]
    forecast: Forecast = {
        ATTR_FORECAST_TIME: item["datetime"].isoformat(),
        ATTR_FORECAST_NATIVE_TEMP: item["temperature"],
        ATTR_FORECAST_NATIVE_APPARENT_TEMP: item["apparentTemperature"],
        ATTR_FORECAST_HUMIDITY: item["humidity"],
        ATTR_FORECAST_SYMBOL: symbol,
        ATTR_FORECAST_SYMBOLTEXT: symbol_text,
        # PV-relevant extras from wo-cloud (Faza 1).
        # ATTR_FORECAST_PRECIPITATION_PROBABILITY is a standard HA key —
        # use it so HA frontends recognize the value automatically.
        ATTR_FORECAST_PRECIPITATION_PROBABILITY: item.get(
            "precipitation_probability"
        ),
        "precipitation_amount_mm_min": item.get("precipitation_amount_mm_min"),
        "precipitation_amount_mm_max": item.get("precipitation_amount_mm_max"),
        "precipitation_duration_min_min": item.get(
            "precipitation_duration_min_min"
        ),
        "precipitation_duration_min_max": item.get(
            "precipitation_duration_min_max"
        ),
        "precipitation_type": item.get("precipitation_type"),
        "convection_probability": item.get("convection_probability"),
        "visibility_meter": item.get("visibility_meter"),
        "smog_level": item.get("smog_level"),
        "dew_point_celsius": item.get("dew_point_celsius"),
        "air_pressure_hpa": item.get("air_pressure_hpa"),
        "wind_speed_kmh": item.get("wind_speed_kmh"),
        "wind_direction_deg": item.get("wind_direction_deg"),
        # 15-min sub-hour granularity for the nearest ~105 min, derived
        # from wo-cloud's `nowcast_trend`. Empty list when out of nowcast
        # range (>105 min ahead) or when nowcast is unavailable.
        "nowcast_15min": item.get("nowcast_15min", []),
    }
    _set_condition(forecast, symbol, symbol_text)
    _set_custom_condition(forecast, symbol, symbol_text)
    return forecast


def _set_condition(
    forecast: Forecast, symbol: str, symbol_text: str
) -> None:
    mapped_symbol = SYMBOLTEXT_CONDITION_MAP.get(symbol)
    condition = mapped_symbol if mapped_symbol else symbol
    forecast[ATTR_FORECAST_CONDITION] = condition


def _set_custom_condition(
    forecast: Forecast, symbol: str, symbol_text: str
) -> None:
    mapped_symbol = SYMBOLTEXT_CONDITION_CUSTOM_MAP.get(symbol)
    mapped_symbol_text = SYMBOLTEXT_CONDITION_CUSTOM_MAP.get(symbol_text)
    if mapped_symbol and mapped_symbol_text:
        forecast[ATTR_FORECAST_CONDITION_CUSTOM] = mapped_symbol
        if mapped_symbol != mapped_symbol_text:
            forecast[ATTR_FORECAST_CONDITION_SYMBOL] = mapped_symbol
            forecast[ATTR_FORECAST_CONDITION_SYMBOLTEXT] = mapped_symbol_text
    elif mapped_symbol:
        forecast[ATTR_FORECAST_CONDITION_CUSTOM] = mapped_symbol
        forecast[ATTR_FORECAST_CONDITION_SYMBOL] = mapped_symbol
        forecast[ATTR_FORECAST_CONDITION_SYMBOLTEXT] = ATTR_CONDITION_UNKNOWN
    elif mapped_symbol_text:
        forecast[ATTR_FORECAST_CONDITION_CUSTOM] = symbol
        forecast[ATTR_FORECAST_CONDITION_SYMBOL] = ATTR_CONDITION_UNKNOWN
        forecast[ATTR_FORECAST_CONDITION_SYMBOLTEXT] = mapped_symbol_text
    else:
        forecast[ATTR_FORECAST_CONDITION_CUSTOM] = symbol
        forecast[ATTR_FORECAST_CONDITION_SYMBOL] = ATTR_CONDITION_UNKNOWN
        forecast[ATTR_FORECAST_CONDITION_SYMBOLTEXT] = ATTR_CONDITION_UNKNOWN


def _synthesize_current_hour(
    inp: HourlyForecastInput, now: datetime
) -> Forecast | None:
    """Build a `Forecast` entry for the current clock hour from cached + live data.

    Returns None only when current observations are entirely missing (right
    after install, before the first successful fetch). When
    `nexthour_cache_current` is absent or stale (warm-up window, long outage),
    the cache-sourced fields fall back to None — the synthesis still returns
    a useful entry from live observations + nowcast.
    """
    obs = inp.current_observations
    if not obs:
        return None
    cache_current = inp.nexthour_cache_current or {}

    current_hour = now.replace(minute=0, second=0, microsecond=0)
    symbol = obs.get("symbol", "")
    symbol_text = symbol

    forecast: Forecast = {
        ATTR_FORECAST_TIME: current_hour.isoformat(),
        ATTR_FORECAST_NATIVE_TEMP: obs.get("temperature"),
        ATTR_FORECAST_NATIVE_APPARENT_TEMP: obs.get("apparentTemperature"),
        ATTR_FORECAST_HUMIDITY: obs.get("humidity"),
        ATTR_FORECAST_PRECIPITATION_PROBABILITY: obs.get(
            "precipitation_probability"
        ),
        ATTR_FORECAST_SYMBOL: symbol,
        ATTR_FORECAST_SYMBOLTEXT: symbol_text,
        # Cache-sourced — hour-forecast for the current hour, captured
        # before it became current (typically the :59:30 forced fetch).
        "precipitation_amount_mm_min": cache_current.get(
            "precipitation_amount_mm_min"
        ),
        "precipitation_amount_mm_max": cache_current.get(
            "precipitation_amount_mm_max"
        ),
        "precipitation_duration_min_min": cache_current.get(
            "precipitation_duration_min_min"
        ),
        "precipitation_duration_min_max": cache_current.get(
            "precipitation_duration_min_max"
        ),
        "convection_probability": cache_current.get("convection_probability"),
        "visibility_meter": cache_current.get("visibility_meter"),
        # Live point-in-time — semantically "now", not hour aggregate.
        "precipitation_type": obs.get("precipitation_type"),
        "smog_level": obs.get("smog_level"),
        "dew_point_celsius": obs.get("dew_point_celsius"),
        "air_pressure_hpa": obs.get("air_pressure_hpa"),
        "wind_speed_kmh": obs.get("wind_speed_kmh"),
        "wind_direction_deg": obs.get("wind_direction_deg"),
        # 15-min sub-hour items for the current hour (some slots may be
        # past from a real-time perspective; consumers can filter).
        "nowcast_15min": _nowcast_items_for_current_hour(inp.nowcast_items, now),
        # When the coordinator last fetched any wo-cloud data. Purely
        # informational — lets consumers display data freshness.
        "fetched_at": (
            inp.last_fetched_at.isoformat() if inp.last_fetched_at else None
        ),
    }
    _set_condition(forecast, symbol, symbol_text)
    _set_custom_condition(forecast, symbol, symbol_text)
    return forecast


def _nowcast_items_for_current_hour(
    nowcast_items: list[dict[str, Any]], now: datetime
) -> list[dict[str, Any]]:
    if not nowcast_items:
        return []
    out: list[dict[str, Any]] = []
    for item in nowcast_items:
        try:
            dt = datetime.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue
        if dt.date() == now.date() and dt.hour == now.hour:
            out.append(item)
    return out


def _same_hour(iso_a: str, iso_b: str) -> bool:
    """True when two ISO timestamps share (date, hour)."""
    try:
        a = datetime.fromisoformat(iso_a)
        b = datetime.fromisoformat(iso_b)
    except (TypeError, ValueError):
        return False
    return a.date() == b.date() and a.hour == b.hour
