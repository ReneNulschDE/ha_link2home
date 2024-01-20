"""Config flow for NEW_NAME integration."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectionError, ClientError
import voluptuous as vol  # type: ignore

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LOGGER, VERIFY_SSL
from .webapi import Link2HomeWebApi

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): selector.TextSelector(),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
        ),
    }
)


class Link2HomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config or options flow for Link2Home."""

    VERSION = 1

    def __init__(self):
        """Initialize component."""
        self._existing_entry = None
        self.data = None
        self.reauth_mode = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Get configuration from the user."""

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)

        errors = {}

        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]

        await self.async_set_unique_id(username)
        if not self.reauth_mode:
            self._abort_if_unique_id_configured()

        webapi: Link2HomeWebApi = Link2HomeWebApi(
            self.hass, async_get_clientsession(self.hass, VERIFY_SSL), username, password
        )

        try:
            (
                login_result,
                login_result_code,
                login_result_msg,
            ) = await webapi.login()
            LOGGER.debug(
                "result: %s, code: %s, msg: %s", login_result, login_result_code, login_result_msg
            )
            if login_result:
                LOGGER.debug("Login successful. Creating config entry")
            elif not login_result and login_result_code != 0:
                errors["base"] = f"Invalid credentials: {login_result_msg}"
                return self.async_show_form(
                    step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
                )
            elif not login_result and login_result_code == 0:
                errors[
                    "base"
                ] = "Unknown login error. Please check the logs with diagnostic mode on."
                return self.async_show_form(
                    step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
                )
        except (ClientError, ClientConnectionError) as error:
            LOGGER.debug("Can't connect to the Link2Home cloud.", error)
            errors[
                "base"
            ] = "Can't connect to the Link2Home cloud. Please check the logs with diagnostic mode on."
        except Exception as error:
            LOGGER.debug("Unknown error connecting Link2Home cloud.", error)
            errors[
                "base"
            ] = "Unknown error connecting to the Link2Home cloud. Please check the logs with diagnostic mode on."
        else:
            return self.async_create_entry(
                title=username,
                data={},
                options={CONF_USERNAME: username, CONF_PASSWORD: password},
            )

        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA, errors=errors)

    async def async_step_reauth(self, user_input=None):
        """Get new tokens for a config entry that can't authenticate."""

        self.reauth_mode = True
        self._existing_entry = user_input

        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)
