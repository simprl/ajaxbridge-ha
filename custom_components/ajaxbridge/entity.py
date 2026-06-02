"""Base entity helpers for ajaxbridge."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AjaxbridgeCoordinator, AjaxbridgeEntityDescription


class AjaxbridgeEntity(CoordinatorEntity[AjaxbridgeCoordinator]):
    """Base ajaxbridge entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AjaxbridgeCoordinator,
        description: AjaxbridgeEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description_data = description
        self._attr_unique_id = description.key
        self._attr_name = description.name

        if description.device_key:
            device = coordinator.data.devices.get(description.device_key, {})
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, description.device_key)},
                name=device.get("name", description.device_key),
                manufacturer=device.get("manufacturer"),
                model=device.get("model"),
            )

    @property
    def entity_data(self) -> AjaxbridgeEntityDescription:
        """Return the current entity data."""
        return self.coordinator.data.entities.get(
            self.entity_description_data.key,
            self.entity_description_data,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return bool(self.entity_data.available)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return dict(self.entity_data.attributes)


def setup_dynamic_entities(
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
    async_add_entities: AddEntitiesCallback,
    platform: str,
    factory: Callable[[AjaxbridgeCoordinator, AjaxbridgeEntityDescription], Entity],
) -> None:
    """Add entities for a platform and subscribe for new state-model entities."""
    added_keys: set[str] = set()

    def add_new_entities() -> None:
        entities = []
        for entity in coordinator.data.entities.values():
            if entity.platform != platform or entity.key in added_keys:
                continue
            added_keys.add(entity.key)
            entities.append(factory(coordinator, entity))

        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))
