"""Support for the WetterOnline service."""

from __future__ import annotations

from datetime import UTC, date, datetime
import logging
from typing import Any, cast

from homeassistant.components.weather import (
    ATTR_FORECAST_CLOUD_COVERAGE,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_APPARENT_TEMP,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_GUST_SPEED,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_UV_INDEX,
    ATTR_FORECAST_WIND_BEARING,
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    CONF_NAME,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import now as now_local

from . import WetterOnlineConfigEntry
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
from .coordinator import WeatherOnlineDataUpdateCoordinator

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WetterOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a WetterOnline weather entity from a config_entry."""
    async_add_entities([WetterOnlineEntity(entry.runtime_data, entry.data[CONF_NAME])])


class WetterOnlineEntity(
    SingleCoordinatorWeatherEntity[WeatherOnlineDataUpdateCoordinator]
):
    """Define an WetterOnline entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, coordinator: WeatherOnlineDataUpdateCoordinator, name: str
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_visibility_unit = UnitOfLength.KILOMETERS
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._attr_unique_id = name
        self._attr_device_info = coordinator.device_info
        self._attr_supported_features = (
            WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
        )
        self.coordinator: WeatherOnlineDataUpdateCoordinator = coordinator
        self._last_hourly_forecast: list[Forecast] = None
        self._last_hourly_forecast_day: date = None

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        return _map_symbol_to_condition(
            self.coordinator.data.current_observations["symbol"]
        )

    @property
    def native_temperature(self) -> float:
        """Return the temperature."""
        return cast(float, self.coordinator.data.current_observations["temperature"])

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return [
            {
                ATTR_FORECAST_TIME: item["datetime"].astimezone(UTC).isoformat(),
                ATTR_FORECAST_NATIVE_TEMP: item["maxTemperature"],
                ATTR_FORECAST_NATIVE_TEMP_LOW: item["minTemperature"],
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: item[
                    "precipitationProbability"
                ],
                # ATTR_FORECAST_CONDITION: _map_symbol_to_condition(item["symbolText"]),
                # ATTR_FORECAST_CLOUD_COVERAGE: item["CloudCoverDay"],
                # ATTR_FORECAST_HUMIDITY: item["RelativeHumidityDay"]["Average"],
                # ATTR_FORECAST_NATIVE_APPARENT_TEMP: item["RealFeelTemperatureMax"][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_NATIVE_PRECIPITATION: item["TotalLiquidDay"][ATTR_VALUE],
                # ATTR_FORECAST_NATIVE_WIND_SPEED: item["WindDay"][ATTR_SPEED][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_NATIVE_WIND_GUST_SPEED: item["WindGustDay"][ATTR_SPEED][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_UV_INDEX: item["UVIndex"][ATTR_VALUE],
                # ATTR_FORECAST_WIND_BEARING: item["WindDay"][ATTR_DIRECTION]["Degrees"],
            }
            for item in self.coordinator.data.daily_forecast
        ]

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast in native units."""
        return [
            self._hourly_forecast_item(item)
            for item in self.coordinator.data.hourly_forecast
        ]

    def _hourly_forecast_item(self, item: dict[str, Any]) -> Forecast:
        symbol = item["symbol"]
        symbol_text = item["symbolText"]
        forecast = {
            ATTR_FORECAST_TIME: item["datetime"].isoformat(),
            ATTR_FORECAST_NATIVE_TEMP: item["temperature"],
            ATTR_FORECAST_NATIVE_APPARENT_TEMP: item["apparentTemperature"],
            ATTR_FORECAST_HUMIDITY: item["humidity"],
            ATTR_FORECAST_SYMBOL: symbol,
            ATTR_FORECAST_SYMBOLTEXT: symbol_text,
        }
        self._set_condition(forecast, symbol, symbol_text)
        self._set_custom_condition(forecast, symbol, symbol_text)
        return forecast

    def _set_condition(self, forecast, symbol, symbol_text):
        mapped_symbol = SYMBOLTEXT_CONDITION_MAP.get(symbol)
        condition = mapped_symbol if mapped_symbol else symbol
        forecast[ATTR_FORECAST_CONDITION] = condition

    def _set_custom_condition(self, forecast: Forecast, symbol: str, symbol_text: str):
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

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()


def _map_symbol_to_condition(symbol: str) -> str:
    return SYMBOLTEXT_CONDITION_MAP.get(symbol, symbol)
