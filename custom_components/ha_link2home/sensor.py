"""Link2Home Sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from homeassistant import util
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_CONNECTIONS, ATTR_SW_VERSION, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import Link2HomeDataUpdateCoordinator
from .model import Link2HomeDevice


@dataclass(frozen=True)
class Link2HomeSensorDescriptionMixin:
    """Mixin for Link2Home sensor."""

    value_fn: Callable[[dict[str, Any]], str | int | float | datetime | None]


@dataclass(frozen=True)
class Link2HomeSensorDescription(SensorEntityDescription, Link2HomeSensorDescriptionMixin):
    """Class describing Link2Home sensor entities."""

    attr_fn: Callable[[Any | None], dict[str, Any]] = lambda _: {}


SENSOR_TYPES: tuple[Link2HomeSensorDescription, ...] = (
    Link2HomeSensorDescription(
        key="online",
        device_class=None,
        entity_registry_enabled_default=True,
        native_unit_of_measurement=None,
        state_class=None,
        translation_key="online",
        value_fn=lambda data: cast(bool, data),
    ),
    Link2HomeSensorDescription(
        key="channel1",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda data: cast(str, data),
        state_class=None,
        native_unit_of_measurement=None,
        translation_key="channel1",
    ),
    Link2HomeSensorDescription(
        key="channel2",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda data: cast(str, data),
        state_class=None,
        native_unit_of_measurement=None,
        translation_key="channel2",
    ),
    Link2HomeSensorDescription(
        key="last_operation",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda data: cast(datetime, data),
        state_class=None,
        native_unit_of_measurement=None,
        translation_key="channel2",
    ),
    Link2HomeSensorDescription(
        key="last_operation_local",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda data: cast(datetime, data),
        state_class=None,
        native_unit_of_measurement=None,
        translation_key="channel2",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Link2Home integration from a config entry."""

    coordinator: Link2HomeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    data: list[Link2HomeDevice] = list(coordinator.data.values())

    for result in data:
        device_sensors = result.__dir__()
        entities.extend(
            [
                Link2HomeSensor(result, coordinator, description)
                for description in SENSOR_TYPES
                if description.key in device_sensors
            ]
        )
    LOGGER.debug("async_setup_entry: Sensor count for creation - %s", len(entities))
    async_add_entities(entities)


class Link2HomeSensor(CoordinatorEntity[Link2HomeDataUpdateCoordinator], SensorEntity):
    """Link2Home Sensor."""

    _attr_has_entity_name = True
    entity_description: Link2HomeSensorDescription

    def __init__(
        self,
        device: Link2HomeDevice,
        coordinator: Link2HomeDataUpdateCoordinator,
        description: Link2HomeSensorDescription,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = util.slugify(f"{device.mac_address} {description.key}")
        self._attr_name = description.key
        self._attr_should_poll = False

        self.entity_description = description
        self.device: Link2HomeDevice = device
        self._sensor_data = getattr(coordinator.data.get(device.mac_address), description.key)

    @property
    def native_value(self) -> str | int | float | datetime | None:
        """Return the state."""
        return self.entity_description.value_fn(self._sensor_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""

        return self.entity_description.attr_fn(self.coordinator.data.get(self.device.mac_address))

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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._sensor_data = getattr(
            self.coordinator.data.get(self.device.mac_address),
            self.entity_description.key,
        )
        self.async_write_ha_state()
