"""Binary sensor platform for ajaxbridge."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AjaxbridgeCoordinator
from .entity import AjaxbridgeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from the state model."""
    coordinator: AjaxbridgeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        AjaxbridgeBinarySensor(coordinator, entity)
        for entity in coordinator.data.entities.values()
        if entity.platform == "binary_sensor"
    )


class AjaxbridgeBinarySensor(AjaxbridgeEntity, BinarySensorEntity):
    """Ajaxbridge binary sensor."""

    @property
    def is_on(self) -> bool | None:
        """Return binary state."""
        state = self.entity_data.state
        if state is None:
            return None
        return bool(state)

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return device class."""
        device_class = self.entity_data.device_class
        if not device_class:
            return None
        try:
            return BinarySensorDeviceClass(device_class)
        except ValueError:
            return None
