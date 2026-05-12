"""WetterOnline sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_NAME,
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import WetterOnlineConfigEntry
from .coordinator import WeatherOnlineDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class WetterOnlineSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor over current_observations."""

    value_fn: Callable[[dict[str, Any]], Any]


# Numeric sensors — `state_class="measurement"` → automatic LTS (statistics
# hourly mean/min/max preserved beyond recorder purge).
NUMERIC_SENSORS: tuple[WetterOnlineSensorDescription, ...] = (
    WetterOnlineSensorDescription(
        key="temperature",
        translation_key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("temperature"),
    ),
    WetterOnlineSensorDescription(
        key="apparent_temperature",
        name="Apparent Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("apparentTemperature"),
    ),
    WetterOnlineSensorDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("humidity"),
    ),
    WetterOnlineSensorDescription(
        key="dew_point",
        name="Dew Point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("dew_point_celsius"),
    ),
    WetterOnlineSensorDescription(
        key="pressure",
        name="Pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("air_pressure_hpa"),
    ),
    WetterOnlineSensorDescription(
        key="wind_speed",
        name="Wind Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("wind_speed_kmh"),
    ),
    WetterOnlineSensorDescription(
        key="wind_bearing",
        name="Wind Bearing",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("wind_direction_deg"),
    ),
    WetterOnlineSensorDescription(
        key="precipitation_probability",
        name="Precipitation Probability",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("precipitation_probability"),
    ),
    WetterOnlineSensorDescription(
        key="precipitation_amount_mm_min",
        name="Precipitation Amount Min",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("precipitation_amount_mm_min"),
    ),
    WetterOnlineSensorDescription(
        key="precipitation_amount_mm_max",
        name="Precipitation Amount Max",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("precipitation_amount_mm_max"),
    ),
    WetterOnlineSensorDescription(
        key="precipitation_duration_min_min",
        name="Precipitation Duration Min",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("precipitation_duration_min_min"),
    ),
    WetterOnlineSensorDescription(
        key="precipitation_duration_min_max",
        name="Precipitation Duration Max",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("precipitation_duration_min_max"),
    ),
    WetterOnlineSensorDescription(
        key="solar_elevation",
        name="Solar Elevation",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("solar_elevation"),
    ),
    WetterOnlineSensorDescription(
        key="air_pressure_tendency",
        name="Air Pressure Tendency",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("air_pressure_tendency_category"),
    ),
)

# String sensors — no LTS (statistics only supports numeric), but state
# changes still archived in `states` table for the recorder retention window.
STRING_SENSORS: tuple[WetterOnlineSensorDescription, ...] = (
    WetterOnlineSensorDescription(
        key="precipitation_type",
        name="Precipitation Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("precipitation_type"),
    ),
    WetterOnlineSensorDescription(
        key="smog_level",
        name="Smog Level",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("smog_level"),
    ),
    WetterOnlineSensorDescription(
        key="weather_condition_image",
        name="Weather Condition Image",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda obs: obs.get("weather_condition_image"),
    ),
)


# Nexthour sensors — back-fed from the sliding-window cache that
# `coordinator.nexthour_cache["current"]` keeps. wo-cloud's `current` payload
# lacks these fields; they only appear in `hours[]`, so we have to remember
# the upcoming-hour data fetched in the previous hour and promote it on
# rollover (see coordinator._update_nexthour_cache).
NEXTHOUR_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="visibility",
        name="Visibility",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="convection_probability",
        name="Convection Probability",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

NEXTHOUR_FIELD_BY_KEY = {
    "visibility": "visibility_meter",
    "convection_probability": "convection_probability",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WetterOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add WetterOnline sensor entities from a config_entry."""
    coordinator = entry.runtime_data
    name = entry.data[CONF_NAME]
    entities: list[SensorEntity] = [
        WetterOnlineConditionCustomSensor(coordinator, name),
    ]
    entities.extend(
        WetterOnlineObservationSensor(coordinator, name, desc)
        for desc in (*NUMERIC_SENSORS, *STRING_SENSORS)
    )
    entities.extend(
        WetterOnlineNexthourSensor(coordinator, name, desc)
        for desc in NEXTHOUR_SENSORS
    )
    async_add_entities(entities)


class WetterOnlineConditionCustomSensor(
    CoordinatorEntity[WeatherOnlineDataUpdateCoordinator], SensorEntity
):
    """Current condition_custom (granular palette) as persistent sensor state.

    Reads precomputed `condition_custom` from `current_observations` (derived
    in wetteronline_api.py::async_get_weather from current symbol via
    SYMBOLTEXT_CONDITION_CUSTOM_MAP).

    Update event-driven via CoordinatorEntity — every coordinator refresh
    (every 5 min). HA dedupes unchanged states → recorder only writes real
    changes.
    """

    _attr_has_entity_name = True
    _attr_name = "Condition Custom"

    def __init__(
        self, coordinator: WeatherOnlineDataUpdateCoordinator, name: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{name}_condition_custom"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or not data.current_observations:
            return None
        return data.current_observations.get("condition_custom") or None


class WetterOnlineObservationSensor(
    CoordinatorEntity[WeatherOnlineDataUpdateCoordinator], SensorEntity
):
    """Single value read from coordinator's current_observations dict.

    One entity per `WetterOnlineSensorDescription` — numeric ones get LTS
    via `state_class="measurement"`, string ones store raw state only.
    """

    _attr_has_entity_name = True
    entity_description: WetterOnlineSensorDescription

    def __init__(
        self,
        coordinator: WeatherOnlineDataUpdateCoordinator,
        name: str,
        description: WetterOnlineSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{name}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data or not data.current_observations:
            return None
        return self.entity_description.value_fn(data.current_observations)


class WetterOnlineNexthourSensor(
    CoordinatorEntity[WeatherOnlineDataUpdateCoordinator], SensorEntity
):
    """Sensor backed by `coordinator.nexthour_cache["current"]`.

    Returns `None` when the cached `current.hour_iso` does not match the
    real-time clock hour (cache stale after a long outage, or warming up
    after a fresh install before the first hour rollover).
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WeatherOnlineDataUpdateCoordinator,
        name: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{name}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> Any:
        current = self.coordinator.nexthour_cache.get("current") if (
            self.coordinator.nexthour_cache
        ) else None
        if not current:
            return None
        if not _matches_current_hour(current.get("hour_iso")):
            return None
        field = NEXTHOUR_FIELD_BY_KEY[self.entity_description.key]
        return current.get(field)


def _matches_current_hour(iso: str | None) -> bool:
    if not iso:
        return False
    try:
        stored = datetime.fromisoformat(iso)
    except ValueError:
        return False
    now = dt_util.now()
    return stored.date() == now.date() and stored.hour == now.hour
