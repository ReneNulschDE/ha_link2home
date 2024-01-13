"""Support for Blink Motion detection switches."""
from __future__ import annotations

import asyncio
from typing import Any, cast

from homeassistant import util
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_CONNECTIONS, ATTR_SW_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import Link2HomeDataUpdateCoordinator
from .model import Link2HomeDevice

SWITCH_TYPES: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key="channel1",
        translation_key="switch_channel1",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    SwitchEntityDescription(
        key="channel2",
        translation_key="switch_channel2",
        device_class=SwitchDeviceClass.SWITCH,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Link2Home switches."""

    coordinator: Link2HomeDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
    data: list[Link2HomeDevice] = list(coordinator.data.values())
    entities = []

    for result in data:
        if result.channel1 != "XX":
            entities.append(Link2HomeSwitch(result, coordinator, SWITCH_TYPES[0]))
        if result.channel2 != "XX":
            entities.append(Link2HomeSwitch(result, coordinator, SWITCH_TYPES[1]))

    LOGGER.debug("async_setup_entry: Switch count for creation - %s", len(entities))

    async_add_entities(entities)


class Link2HomeSwitch(CoordinatorEntity[Link2HomeDataUpdateCoordinator], SwitchEntity):
    """Representation of a Blink motion detection switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: Link2HomeDevice,
        coordinator: Link2HomeDataUpdateCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.device = device
        self.entity_description = description
        self._attr_unique_id = util.slugify(f"{device.mac_address} {description.key}")
        self._attr_name = description.key
        self._attr_should_poll = False

        self.channel = self.entity_description.key[-1:].zfill(2)
        self._sensor_data = getattr(coordinator.data.get(device.mac_address), description.key)

    @property
    def device_info(self) -> DeviceInfo:
        """Device information."""
        info = DeviceInfo(
            identifiers={(DOMAIN, self.device.mac_address)},
            manufacturer="Link2Home",
            model=self.device.device_type,
            name=(
                self.device.device_name
                or cast(ConfigEntry, self.coordinator.config_entry).title
                or f"{self.device.device_type} ({self.device.mac_address})"
            ),
        )

        if self.device.mac_address:
            info[ATTR_CONNECTIONS] = {(dr.CONNECTION_NETWORK_MAC, self.device.mac_address)}

        if self.device.version:
            info[ATTR_SW_VERSION] = self.device.version

        return info

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""

        state = {"channel": self.channel}
        return state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            self.coordinator.set_state(self.device, True, self.channel)

        except asyncio.TimeoutError as er:
            raise HomeAssistantError("Blink failed to arm camera motion detection") from er

        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            self.coordinator.set_state(self.device, False, self.channel)

        except asyncio.TimeoutError as er:
            raise HomeAssistantError(
                f"Link2Home failed to switch of channel {self.channel} of the device {self.device_info.name}"  # type: ignore
            ) from er

        await self.coordinator.async_refresh()

    @property
    def is_on(self) -> bool:
        """Return if switch is enabled."""
        return self._sensor_data == "ff"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._sensor_data = getattr(
            self.coordinator.data.get(self.device.mac_address),
            self.entity_description.key,
        )
        self.async_write_ha_state()
