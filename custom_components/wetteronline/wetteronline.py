import bs4
import ast
import html
## non std lib: requests, bs4, lxml
from datetime import datetime,timedelta,timezone
from typing import Final, Any
from aiohttp import ClientSession

from dataclasses import dataclass

MIDNIGHT: Final = datetime.min.time()
HTTP_HEADERS: dict[str, str] = {
    "Accept-Encoding": "gzip",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
}


@dataclass
class WetterOnlineData:
    """Data from WetterOnline."""
    current_observations: dict[str, Any]
    daily_forecast: list[dict[str, Any]]
    hourly_forecast: list[dict[str, Any]]


class WetterOnline:
    """Main class to perform WetterOnline requests."""

    def __init__(self, session: ClientSession, url: str) -> None:
        self._session = session
        self._complete_url = f"https://www.wetteronline.de/{url}"

    async def async_get_weather(self) -> WetterOnlineData:
        async with self._session.get(self._complete_url,
                                     headers=HTTP_HEADERS,
                                     allow_redirects= False) as resp:
            raw_html = html.unescape(await resp.text())
            weather_utils = WeatherUtils(raw_html)
            return WetterOnlineData(
                current_observations=weather_utils.current_observations(),
                daily_forecast=weather_utils.daily_forecast(),
                hourly_forecast=weather_utils.hourly_forecast()
            )


class WeatherUtils:

    def __init__(self, raw_html = None):
        """
        Initialize BeautifulSoup object with raw html
        """
        self.soup = bs4.BeautifulSoup(raw_html, "lxml")

    def current_observations(self) -> dict[str, Any]:
        """ Returns the current observations 4 day forecast of the given `url`. """

        temperature = (self.soup
                       .find("div", {"id": "nowcast-card-temperature"})
                       .find("div", {"class":"value"})
                       .text)
        return {
            "temperature": temperature,
            "symbol": "symbol"
        }


    def hourly_forecast(self) -> list[dict[str, Any]]:
        """ Returns the hourly forecast of the given `url` for today and tomorrow. """

        today = datetime.combine(datetime.today(), MIDNIGHT)
        tomorrow = today + timedelta(days = 1)

        scripts = (self.soup
                   .find("div", {"id": "hourly-container"})
                   .find_all("script"))
        forecast: list[dict[str, Any]] = []

        replace_keys = {
            "windGusts": "windGustsBft",
            "windDirection": "windDirectionLong",
            "windDirectionShortSector": "windDirection"
        }
        for script in scripts:
            script = str(script).split("({")[1].split("})")[0].strip().replace(" ", "")
            hourly_data_raw = []
            for entry in script.split("\n"):
                key = entry.split(":")[0]
                value = entry.split(":")[1]
                if entry.split(":")[0] in list(replace_keys):
                    hourly_data_raw.append(f'"{replace_keys[entry.split(":")[0]]}": {entry.split(":")[1]}')
                else:
                    hourly_data_raw.append(f'"{entry.split(":")[0]}": {entry.split(":")[1]}')
            hourly_data = ast.literal_eval("{" + "".join(hourly_data_raw) + "}")

            ## delete useless keys
            hourly_data.pop("docrootVersion", None)
            # for key in ["dayTime", "daySynonym", "docrootVersion", "windSpeedText", "windDirectionLong"]:
            #    smallreturndict.pop(key, None)
            ## delete unknown keys
            # for key in ["smog", "tierAppendix", "symbol", "symbolText", "windy", "weatherInfoIndex"]:
            #    smallreturndict.pop(key, None)

            daySynonym = hourly_data['daySynonym']
            match daySynonym:
                case "heute":
                    forecast_day = today
                case "morgen":
                    forecast_day = tomorrow
                case _:
                    raise ValueError(f"daySynonym {daySynonym} is different than 'heute' and 'morgen'")

            hour = hourly_data.pop("hour")
            date_with_hour = forecast_day.replace(hour = hour)
            hourly_data['datetime'] = date_with_hour.astimezone(timezone.utc)

            forecast.append(hourly_data)

        return forecast

    def daily_forecast(self) -> list[dict[str, Any]]:
        """ Returns the full 4 day forecast of the given `url`. """

        ## get dates first
        forecast : list[dict[str, Any]] = []
        for i in self.soup.find("table", {"id":"daterow"}).find_all("th"):
            date = i.find("span").text
            if "," in list(date):
                date = date.split(", ")[1]
            forecast.append({'date': date})

        weathertable = self.soup.find("table", {"id": "weather"})
        ## maxtemp
        taglist = list(weathertable.find("tr", {"class": "Maximum Temperature"}).find_all("div"))
        for i in range(len(taglist)):
            tag = taglist[i].find_all("span")[1]
            forecast[i]["maxTemperature"] = int(str(tag.text).rstrip("°"))

        ## mintemp
        taglist = list(weathertable.find("tr", {"class": "Minimum Temperature"}).find_all("div"))
        for i in range(len(taglist)):
            tag = taglist[i].find_all("span")[1]
            forecast[i]["minTemperature"] = int(str(tag.text).rstrip("°"))

        ## sunhours
        taglist = list(weathertable.find("tr", {"id": "sun_teaser"}).find_all("span"))
        for i in range(len(taglist)):
            tag = taglist[i]
            forecast[i]["sunHours"] = int(str(tag.text).lstrip().rstrip(" Std.\n"))

        ## precipitation probability
        taglist = list(weathertable.find("tr", {"id": "precipitation_teaser"}).find_all("span"))
        for i in range(len(taglist)):
            tag = taglist[i]
            forecast[i]["precipitationProbability"] = int(str(tag.text).lstrip().rstrip(" %\n"))

        return forecast
