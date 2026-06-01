"""Base entity helpers for ajaxbridge."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
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
        return self.coordinator.data.entities[self.entity_description_data.key]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return bool(self.entity_data.available)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return dict(self.entity_data.attributes)

