"""WetterOnline sensors."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WetterOnlineConfigEntry
from .coordinator import WeatherOnlineDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WetterOnlineConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add WetterOnline sensor entities from a config_entry."""
    async_add_entities(
        [WetterOnlineConditionCustomSensor(entry.runtime_data, entry.data[CONF_NAME])]
    )


class WetterOnlineConditionCustomSensor(
    CoordinatorEntity[WeatherOnlineDataUpdateCoordinator], SensorEntity
):
    """Current condition_custom (granular palette) as persistent sensor state.

    Czyta precomputed `condition_custom` z `current_observations`
    (wyliczone w wetteronline_api.py::async_get_weather z current symbol
    przez SYMBOLTEXT_CONDITION_CUSTOM_MAP).

    Update event-driven przez CoordinatorEntity — przy każdym coordinator
    refresh (co 5 min). HA dedupe'uje niezmienione states → recorder
    zapisze tylko prawdziwe zmiany.
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
