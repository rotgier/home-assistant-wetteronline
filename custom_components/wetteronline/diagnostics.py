"""Diagnostics support for WetterOnline."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import WetterOnlineConfigEntry
from .coordinator import WeatherOnlineDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: WetterOnlineConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: WeatherOnlineDataUpdateCoordinator = config_entry.runtime_data

    return {
        "config_entry_data": config_entry.data,
        "observation_data": coordinator.data,
    }
