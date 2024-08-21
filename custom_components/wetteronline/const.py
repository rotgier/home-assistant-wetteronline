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

CONDITION_CLASSES: Final[dict[str, list[int]]] = {
    ATTR_CONDITION_CLEAR_NIGHT: [33, 34, 37],
    ATTR_CONDITION_CLOUDY: [7, 8, 38],
    ATTR_CONDITION_EXCEPTIONAL: [24, 30, 31],
    ATTR_CONDITION_FOG: [11],
    ATTR_CONDITION_HAIL: [25],
    ATTR_CONDITION_LIGHTNING: [15],
    ATTR_CONDITION_LIGHTNING_RAINY: [16, 17, 41, 42],
    ATTR_CONDITION_PARTLYCLOUDY: [3, 4, 6, 35, 36],
    ATTR_CONDITION_POURING: [18],
    ATTR_CONDITION_RAINY: [12, 13, 14, 26, 39, 40],
    ATTR_CONDITION_SNOWY: [19, 20, 21, 22, 23, 43, 44],
    ATTR_CONDITION_SNOWY_RAINY: [29],
    ATTR_CONDITION_SUNNY: [1, 2, 5],
    ATTR_CONDITION_WINDY: [32],
}
CONDITION_MAP = {
    cond_code: cond_ha
    for cond_ha, cond_codes in CONDITION_CLASSES.items()
    for cond_code in cond_codes
}
UPDATE_INTERVAL_WETTERONLINE = timedelta(minutes=15)

CONF_URL_WETTERONLINE: Final = "url_wetteronline"
