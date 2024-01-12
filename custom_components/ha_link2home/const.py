"""Constants for the Link2Home integration."""
import logging

from homeassistant.const import Platform, UnitOfEnergy

LINK2HOME_PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

ATTR_MANUFACTURER = "Link2Home"
DOMAIN = "ha_link2home"
LOGGER = logging.getLogger(__package__)

LOGIN_BASE_URI = "https://userdata.link2home.com"

GENERAL_AUTH_CODE = "7150"


VERIFY_SSL = True
DISABLE_SSL_CERT_CHECK = VERIFY_SSL
SYSTEM_PROXY = None
PROXIES = {}
# SYSTEM_PROXY = "http://192.168.178.61:8080"
# PROXIES = {
#    "https": SYSTEM_PROXY,
# }
