"""Support for the WetterOnline service."""

from __future__ import annotations

from datetime import UTC
from typing import cast

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

from . import WetterOnlineConfigEntry
from .const import SYMBOLTEXT_CONDITION_MAP
from .coordinator import WeatherOnlineDataUpdateCoordinator

PARALLEL_UPDATES = 1


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
            {
                ATTR_FORECAST_TIME: item["datetime"].astimezone(UTC).isoformat(),
                ATTR_FORECAST_CONDITION: _map_symbol_to_condition(item["symbolText"]),
                ATTR_FORECAST_NATIVE_TEMP: item["temperature"],
                ATTR_FORECAST_NATIVE_APPARENT_TEMP: item["apparentTemperature"],
                ATTR_FORECAST_HUMIDITY: item["humidity"],
                # ATTR_FORECAST_CLOUD_COVERAGE: item["CloudCover"],
                # ATTR_FORECAST_NATIVE_PRECIPITATION: item["TotalLiquid"][ATTR_VALUE],
                # ATTR_FORECAST_PRECIPITATION_PROBABILITY: item[
                #     "PrecipitationProbability"
                # ],
                # ATTR_FORECAST_NATIVE_WIND_SPEED: item["Wind"][ATTR_SPEED][ATTR_VALUE],
                # ATTR_FORECAST_NATIVE_WIND_GUST_SPEED: item["WindGust"][ATTR_SPEED][
                #     ATTR_VALUE
                # ],
                # ATTR_FORECAST_UV_INDEX: item["UVIndex"],
                # ATTR_FORECAST_WIND_BEARING: item["Wind"][ATTR_DIRECTION]["Degrees"],
            }
            for item in self.coordinator.data.hourly_forecast
        ]


def _map_symbol_to_condition(symbol: str) -> str:
    return SYMBOLTEXT_CONDITION_MAP.get(symbol, symbol)
