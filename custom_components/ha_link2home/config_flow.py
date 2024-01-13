"""Config flow for NEW_NAME integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LOGGER
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
            async_get_clientsession(self.hass), username, password
        )
        if not await webapi.login():
            LOGGER.info("")
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
            )

        return self.async_create_entry(
            title=username,
            data={},
            options={CONF_USERNAME: username, CONF_PASSWORD: password},
        )

    async def async_step_reauth(self, user_input=None):
        """Get new tokens for a config entry that can't authenticate."""

        self.reauth_mode = True
        self._existing_entry = user_input

        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)
