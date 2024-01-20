"""Constants for the Link2Home integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform

LINK2HOME_PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

ATTR_MANUFACTURER = "Link2Home"
DOMAIN = "ha_link2home"
LOGGER = logging.getLogger(__package__)

USE_SIMULATOR = False
LOGIN_BASE_URI_CLOUD = "https://userdata.link2home.com"
LOGIN_BASE_URI_SIMULATOR = "http://0.0.0.0:8000"
LOGIN_BASE_URI = LOGIN_BASE_URI_CLOUD if not USE_SIMULATOR else LOGIN_BASE_URI_SIMULATOR
GENERAL_AUTH_CODE = "7150"


USE_PROXY = False
VERIFY_SSL = True
SYSTEM_PROXY: str | None = "http://192.168.178.61:8080" if USE_PROXY else None
PROXIES: dict | None = {"https": SYSTEM_PROXY} if USE_PROXY else {}
