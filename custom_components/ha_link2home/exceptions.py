"""Errors for the Link2Home component."""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class Link2HomeException(HomeAssistantError):
    """Base class for Link2Home exceptions."""


class Link2HomeCloudAuthException(Link2HomeException):
    """Cloud authentication errors."""


class Link2HomeCloudConnectException(Link2HomeException):
    """Unable to connect to the cloud."""


class CannotConnectLocal(Link2HomeException):
    """Unable to connect to the cloud."""
