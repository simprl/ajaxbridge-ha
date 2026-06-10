"""Home Assistant registry maintenance for Ajaxbridge."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import AjaxbridgeCoordinator
from .state_model import object_id_from_entity_key

_LOGGER = logging.getLogger(__name__)


async def async_delayed_align_group_entity_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Align group helper entity IDs after HA finishes registering new entities."""
    await asyncio.sleep(2)
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data is None:
        return
    async_sync_registry_metadata(hass, entry, coordinator)


def async_sync_registry_metadata(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Keep HA registry metadata in sync with the latest state model."""
    async_update_device_registry(hass, entry, coordinator)
    async_align_group_entity_ids(hass, entry, coordinator)


def async_update_device_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Update HA device names/models when Ajax REST metadata changes."""
    if not coordinator.data:
        return

    device_registry = dr.async_get(hass)
    for device_key, device in coordinator.data.devices.items():
        device_entry = device_registry.async_get_device(identifiers={(DOMAIN, device_key)})
        if device_entry is None:
            continue
        updates: dict[str, str] = {}
        name = str(device.get("name") or "").strip()
        manufacturer = str(device.get("manufacturer") or "").strip()
        model = str(device.get("model") or "").strip()
        if name and device_entry.name != name:
            updates["name"] = name
        if manufacturer and device_entry.manufacturer != manufacturer:
            updates["manufacturer"] = manufacturer
        if model and device_entry.model != model:
            updates["model"] = model
        if not updates:
            continue
        try:
            device_registry.async_update_device(device_entry.id, **updates)
        except ValueError as err:
            _LOGGER.warning("Cannot update Ajaxbridge device %s metadata: %s", device_key, err)


def async_cleanup_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Remove HA registry entries no longer present in the bridge state model."""
    if not coordinator.data:
        return

    current_entity_keys = set(coordinator.data.entities)
    diagnostics_unique_id = f"{DOMAIN}:{coordinator.client.installation_id}:diagnostics"
    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if registry_entry.unique_id == diagnostics_unique_id:
            continue
        if registry_entry.unique_id in current_entity_keys:
            continue
        entity_registry.async_remove(registry_entry.entity_id)

    current_device_keys = set(coordinator.data.devices)
    device_registry = dr.async_get(hass)
    for device_entry in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        device_keys = {
            identifier
            for domain, identifier in device_entry.identifiers
            if domain == DOMAIN
        }
        if device_keys and device_keys.isdisjoint(current_device_keys):
            device_registry.async_remove_device(device_entry.id)


def async_align_group_entity_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Keep Ajaxbridge entity IDs based on stable Ajax hub/group ids."""
    if not coordinator.data:
        return

    entity_registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    _align_id_based_entity_ids(entity_registry, registry_entries)


def _align_id_based_entity_ids(
    entity_registry: er.EntityRegistry,
    registry_entries: list[er.RegistryEntry],
) -> None:
    for registry_entry in registry_entries:
        object_id = object_id_from_entity_key(registry_entry.unique_id)
        if not object_id or "." not in registry_entry.entity_id:
            continue
        platform = registry_entry.entity_id.split(".", 1)[0]
        desired_entity_id = f"{platform}.{object_id}"
        if registry_entry.entity_id == desired_entity_id:
            continue
        existing_entry = entity_registry.async_get(desired_entity_id)
        if existing_entry is not None and existing_entry.unique_id != registry_entry.unique_id:
            _LOGGER.warning(
                "Cannot rename Ajaxbridge entity %s to %s: target exists",
                registry_entry.entity_id,
                desired_entity_id,
            )
            continue
        try:
            entity_registry.async_update_entity(
                registry_entry.entity_id,
                new_entity_id=desired_entity_id,
            )
        except ValueError as err:
            _LOGGER.warning(
                "Cannot rename Ajaxbridge entity %s to %s: %s",
                registry_entry.entity_id,
                desired_entity_id,
                err,
            )
