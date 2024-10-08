"""Constants for WetterOnline integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
)

DOMAIN: Final = "wetteronline"

# TODO add support for wind forecast
# API_METRIC: Final = "Metric"
# ATTRIBUTION: Final = "Data provided by WetterOnline"
# ATTR_CATEGORY: Final = "Category"
# ATTR_DIRECTION: Final = "Direction"
# ATTR_ENGLISH: Final = "English"
# ATTR_LEVEL: Final = "level"
# ATTR_SPEED: Final = "Speed"
# ATTR_VALUE: Final = "Value"

# MANUFACTURER: Final = "WetterOnline"
# MAX_FORECAST_DAYS: Final = 4

SYMBOLTEXT_CONDITION_MAP: Final[dict[str, str]] = {
    "sonnig": ATTR_CONDITION_SUNNY,
    "so____": ATTR_CONDITION_SUNNY,
    "Gewitter": ATTR_CONDITION_LIGHTNING_RAINY,
    "wb____": ATTR_CONDITION_PARTLYCLOUDY,
    "wechselnd bewölkt": ATTR_CONDITION_PARTLYCLOUDY,
    "wechselndbewölkt": ATTR_CONDITION_PARTLYCLOUDY,
    "bw____": ATTR_CONDITION_PARTLYCLOUDY,
    "bewölkt": ATTR_CONDITION_PARTLYCLOUDY,
    "bws1__": ATTR_CONDITION_RAINY,
    "bws2__": ATTR_CONDITION_RAINY,
    "Schauer": ATTR_CONDITION_RAINY,
    "mo____": ATTR_CONDITION_CLEAR_NIGHT,
    "klar": ATTR_CONDITION_CLEAR_NIGHT,
}

UPDATE_INTERVAL_WETTERONLINE = timedelta(minutes=15)

CONF_URL_WETTERONLINE: Final = "url_wetteronline"
