"""The Link2Home integration."""

from __future__ import annotations

import traceback

from aiohttp import ClientConnectionError, ClientError

from homeassistant.components.network import async_get_source_ip
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LINK2HOME_PLATFORMS, LOGGER, VERIFY_SSL
from .coordinator import Link2HomeDataUpdateCoordinator
from .exceptions import Link2HomeCloudAuthException


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up Link2Home from a config entry."""

    username: str = config_entry.options[CONF_USERNAME]
    password: str = config_entry.options[CONF_PASSWORD]

    websession = async_get_clientsession(hass, VERIFY_SSL)
    local_ip = await async_get_source_ip(hass)

    coordinator = Link2HomeDataUpdateCoordinator(
        hass, websession, username, password, local_ip, config_entry
    )

    try:
        (
            login_result,
            login_result_code,
            login_result_msg,
        ) = await coordinator.webapi.login()
        if not login_result and login_result_code != 0:
            raise ConfigEntryAuthFailed(f"Invalid credentials: {login_result_msg}")
        elif not login_result and login_result_code == 0:
            raise Link2HomeCloudAuthException(
                "Unknown login error. Please check the logs with debug logging on."
            )
    except ConfigEntryAuthFailed as error:
        raise ConfigEntryAuthFailed from error
    except Link2HomeCloudAuthException as error:
        raise Link2HomeCloudAuthException from error
    except (ClientError, ClientConnectionError) as error:
        raise ConfigEntryNotReady from error
    except Exception:
        LOGGER.warning(
            "Unknown error connecting Link2Home cloud. Please check the logs with debug logging on."
        )
        LOGGER.debug(traceback.format_exc())
        return False

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, LINK2HOME_PLATFORMS)

    config_entry.add_update_listener(config_entry_update_listener)

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    LOGGER.debug("Start config_entry_update_listener")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    LOGGER.debug("Start async_unload_entry")

    coordinator: Link2HomeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.udpsession.close()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, LINK2HOME_PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
