"""Config flow for NEW_NAME integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)

from .const import DOMAIN, LOGGER
from .coordinator import Link2HomeDataUpdateCoordinator
from .webapi import Link2HomeWebApi

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): selector.TextSelector(),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
        ),
    }
)


class ConfigFlow(ConfigFlow, domain=DOMAIN):
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

        try:
            webapi: Link2HomeWebApi = Link2HomeWebApi(
                async_get_clientsession(self.hass), username, password
            )
            if not webapi.login():
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
        except Exception:
            raise

    async def async_step_reauth(self, user_input=None):
        """Get new tokens for a config entry that can't authenticate."""

        self.reauth_mode = True
        self._existing_entry = user_input

        return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)
