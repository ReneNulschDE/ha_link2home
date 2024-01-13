"""Constants for the Link2Home integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform

LINK2HOME_PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

ATTR_MANUFACTURER = "Link2Home"
DOMAIN = "ha_link2home"
LOGGER = logging.getLogger(__package__)

LOGIN_BASE_URI = "https://userdata.link2home.com"

GENERAL_AUTH_CODE = "7150"

PROXY_DISABLED = True
DISABLE_SSL_CERT_CHECK = not PROXY_DISABLED
SYSTEM_PROXY: str | None = None if PROXY_DISABLED else "http://192.168.178.61:8080"
PROXIES: dict | None = {} if PROXY_DISABLED else {"https": SYSTEM_PROXY}
