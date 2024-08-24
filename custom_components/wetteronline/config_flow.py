"""Adds config flow for WetterOnline."""

from __future__ import annotations

from asyncio import timeout
import logging
from typing import Any

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientConnectorError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_URL_WETTERONLINE, DOMAIN
from .wetteronline_api import WetterOnline

_LOGGER = logging.getLogger(__name__)


class WetterOnlineFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for WetterOnline."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            websession = async_get_clientsession(self.hass)
            try:
                async with timeout(10):
                    wetteronline = WetterOnline(
                        websession, user_input[CONF_URL_WETTERONLINE]
                    )
                    await wetteronline.async_get_weather()

            except (ClientConnectorError, TimeoutError, ClientError):
                _LOGGER.exception("Cannot connect")
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Error occured")
                errors["base"] = f"other_error: {e!s}"
            else:
                unique_id = user_input[CONF_NAME]
                await self.async_set_unique_id(unique_id, raise_on_progress=False)
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL_WETTERONLINE): str,
                    vol.Optional(
                        CONF_NAME, default=self.hass.config.location_name
                    ): str,
                }
            ),
            errors=errors,
        )
