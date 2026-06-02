"""Sensor platform for ajaxbridge."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AjaxbridgeCoordinator
from .entity import AjaxbridgeEntity, setup_dynamic_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from the state model."""
    coordinator: AjaxbridgeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    setup_dynamic_entities(entry, coordinator, async_add_entities, "sensor", AjaxbridgeSensor)
    async_add_entities([AjaxbridgeDiagnosticsSensor(coordinator)])


class AjaxbridgeSensor(AjaxbridgeEntity, SensorEntity):
    """Ajaxbridge sensor."""

    @property
    def native_value(self):
        """Return sensor value."""
        return self.entity_data.state

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return device class."""
        device_class = self.entity_data.device_class
        if not device_class:
            return None
        try:
            return SensorDeviceClass(device_class)
        except ValueError:
            return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return native unit."""
        unit = self.entity_data.attributes.get("unit_of_measurement")
        return str(unit) if unit else None


class AjaxbridgeDiagnosticsSensor(SensorEntity):
    """Expose HA-side ajaxbridge diagnostics."""

    _attr_has_entity_name = False
    _attr_name = "Ajaxbridge Diagnostics"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AjaxbridgeCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}:{coordinator.client.installation_id}:diagnostics"

    @property
    def native_value(self):
        """Return compact status."""
        return "connected" if self.coordinator.ws_connected else "disconnected"

    @property
    def extra_state_attributes(self) -> dict:
        """Return diagnostic counters."""
        return self.coordinator.diagnostics()
