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
    ATTR_FORECAST_CONDITION,
)

DOMAIN: Final = "wetteronline"

ATTR_FORECAST_SYMBOL = "symbol"
ATTR_FORECAST_SYMBOLTEXT = "symboltext"
ATTR_FORECAST_CONDITION_CUSTOM = ATTR_FORECAST_CONDITION + "_custom"
ATTR_FORECAST_CONDITION_SYMBOL = ATTR_FORECAST_CONDITION_CUSTOM + "_symbol"
ATTR_FORECAST_CONDITION_SYMBOLTEXT = ATTR_FORECAST_CONDITION_CUSTOM + "_symboltext"

ATTR_CONDITION_PARTLYCLOUDY_VARIABLE: Final = ATTR_CONDITION_PARTLYCLOUDY + "-variable"
ATTR_CONDITION_FOG_PARTLY: Final = ATTR_CONDITION_FOG + "-partly"
ATTR_CONDITION_RAINY_LIGHT: Final = ATTR_CONDITION_RAINY + "-light"
ATTR_CONDITION_RAINY_HEAVY: Final = ATTR_CONDITION_RAINY + "-heavy"
ATTR_CONDITION_POURING_LIGHT: Final = ATTR_CONDITION_POURING + "-light"
ATTR_CONDITION_POURING_HEAVY: Final = ATTR_CONDITION_POURING + "-heavy"
ATTR_CONDITION_UNKNOWN: Final = "UNKNOWN"

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
    "so____": ATTR_CONDITION_SUNNY,
    "mo____": ATTR_CONDITION_CLEAR_NIGHT,
    "sonnig": ATTR_CONDITION_SUNNY,
    "klar": ATTR_CONDITION_CLEAR_NIGHT,
    ###############################################
    "wb____": ATTR_CONDITION_EXCEPTIONAL,
    "mb____": ATTR_CONDITION_EXCEPTIONAL,  # same as "wb_" but at night
    "wechselnd bewölkt": ATTR_CONDITION_EXCEPTIONAL,
    "wechselndbewölkt": ATTR_CONDITION_EXCEPTIONAL,
    ###############################################
    "bw____": ATTR_CONDITION_PARTLYCLOUDY,
    "mw____": ATTR_CONDITION_PARTLYCLOUDY,
    "bewölkt": ATTR_CONDITION_PARTLYCLOUDY,
    ###############################################
    "bws1__": ATTR_CONDITION_RAINY,  # light showers WITH sun
    "bws2__": ATTR_CONDITION_RAINY,  # showers WITH sun
    "bws3__": ATTR_CONDITION_RAINY,  # heavy showers WITH sun
    "bds1__": ATTR_CONDITION_RAINY,  # light showers without sun
    "bds2__": ATTR_CONDITION_RAINY,  # showers without sun
    "bds3__": ATTR_CONDITION_RAINY,  # heavy showers without sun
    #########
    "mws1__": ATTR_CONDITION_RAINY,  # light showers WITH moon
    "mws2__": ATTR_CONDITION_RAINY,  # showers WITH moon
    "mws3__": ATTR_CONDITION_RAINY,  # heavy showers WITH moon
    "mds1__": ATTR_CONDITION_RAINY,  # light showers without moon
    "mds2__": ATTR_CONDITION_RAINY,  # showers without moon
    "mds3__": ATTR_CONDITION_RAINY,  # heavy showers without moon
    #########
    "Schauer": ATTR_CONDITION_RAINY,
    ###############################################
    "bwr1__": ATTR_CONDITION_POURING,  # light rain WITH sun
    "bwr2__": ATTR_CONDITION_POURING,  # rain WITH sun
    "bwr3__": ATTR_CONDITION_POURING,  # heavy rain WITH sun
    "bdr1__": ATTR_CONDITION_POURING,  # light rain without sun
    "bdr2__": ATTR_CONDITION_POURING,  # rain without sun
    "bdr3__": ATTR_CONDITION_POURING,  # heavy rain without sun
    #########
    "mwr1__": ATTR_CONDITION_POURING,  # light rain WITH moon
    "mwr2__": ATTR_CONDITION_POURING,  # rain WITH moon
    "mwr3__": ATTR_CONDITION_POURING,  # heavy rain WITH moon
    "mdr1__": ATTR_CONDITION_POURING,  # light rain without moon
    "mdr2__": ATTR_CONDITION_POURING,  # rain without moon
    "mdr3__": ATTR_CONDITION_POURING,  # heavy rain without moon
    #########
    "Regen": ATTR_CONDITION_POURING,
    "leichterRegen": ATTR_CONDITION_POURING,
    ###############################################
    "bd____": ATTR_CONDITION_CLOUDY,  # clouds during day
    "md____": ATTR_CONDITION_CLOUDY,  # clouds same as "md_" but at night
    "stark bewölkt": ATTR_CONDITION_CLOUDY,  # clouds
    "starkbewölkt": ATTR_CONDITION_CLOUDY,  # clouds
    ###############################################
    "Gewitter": ATTR_CONDITION_LIGHTNING_RAINY,
    ###############################################
    "ns____": ATTR_CONDITION_FOG,  # partly foggy
    "teils Nebel, teils Sonne": ATTR_CONDITION_FOG,  # partly foggy
    "nb____": ATTR_CONDITION_FOG,
    "Nebel": ATTR_CONDITION_FOG,
}

SYMBOLTEXT_CONDITION_CUSTOM_MAP: Final[dict[str, str]] = SYMBOLTEXT_CONDITION_MAP.copy()

SYMBOLTEXT_CONDITION_CUSTOM_MAP.update(
    {
        "wb____": ATTR_CONDITION_PARTLYCLOUDY_VARIABLE,
        "mb____": ATTR_CONDITION_PARTLYCLOUDY_VARIABLE,  # same as "wb_" but at night
        "wechselnd bewölkt": ATTR_CONDITION_PARTLYCLOUDY_VARIABLE,
        "wechselndbewölkt": ATTR_CONDITION_PARTLYCLOUDY_VARIABLE,
        ###############################################
        # TODO differentiate WITH and without sun
        "bws1__": ATTR_CONDITION_RAINY_LIGHT + "-partlycloudy",
        "bws2__": ATTR_CONDITION_RAINY + "-partlycloudy",
        "bws3__": ATTR_CONDITION_RAINY_HEAVY + "-partlycloudy",
        "bds1__": ATTR_CONDITION_RAINY_LIGHT,  # light showers without sun
        "bds2__": ATTR_CONDITION_RAINY,  # showers without sun
        "bds3__": ATTR_CONDITION_RAINY_HEAVY,  # heavy showers without sun
        #########
        "mws1__": ATTR_CONDITION_RAINY_LIGHT + "-partlycloudy",
        "mws2__": ATTR_CONDITION_RAINY + "-partlycloudy",
        "mws3__": ATTR_CONDITION_RAINY_HEAVY + "-partlycloudy",
        "mds1__": ATTR_CONDITION_RAINY_LIGHT,  # light showers without moon
        "mds2__": ATTR_CONDITION_RAINY,  # showers without moon
        "mds3__": ATTR_CONDITION_RAINY_HEAVY,  # heavy showers without moon
        ###############################################
        # TODO differentiate WITH and without sun
        "bwr1__": ATTR_CONDITION_POURING_LIGHT + "-partlycloudy",
        "bwr2__": ATTR_CONDITION_POURING + "-partlycloudy",
        "bwr3__": ATTR_CONDITION_POURING_HEAVY + "-partlycloudy",
        "bdr1__": ATTR_CONDITION_POURING_LIGHT,  # light rain without sun
        "bdr2__": ATTR_CONDITION_POURING,  # rain without sun
        "bdr3__": ATTR_CONDITION_POURING_HEAVY,  # heavy rain without sun
        #########
        "mwr1__": ATTR_CONDITION_POURING_LIGHT + "-partlycloudy",
        "mwr2__": ATTR_CONDITION_POURING + "-partlycloudy",
        "mwr3__": ATTR_CONDITION_POURING_HEAVY + "-partlycloudy",
        "mdr1__": ATTR_CONDITION_POURING_LIGHT,  # light rain without moon
        "mdr2__": ATTR_CONDITION_POURING,  # rain without moon
        "mdr3__": ATTR_CONDITION_POURING_HEAVY,  # heavy rain without moon
        #########
        "leichterRegen": ATTR_CONDITION_POURING_LIGHT,
        ###############################################
        "ns____": ATTR_CONDITION_FOG_PARTLY,  # trochę słońca trochę mgły
        "teils Nebel, teils Sonne": ATTR_CONDITION_FOG_PARTLY,  # trochę słońca i mgły
    }
)

UPDATE_INTERVAL_WETTERONLINE = timedelta(minutes=15)

CONF_URL_WETTERONLINE: Final = "url_wetteronline"
