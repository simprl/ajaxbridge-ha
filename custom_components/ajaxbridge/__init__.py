"""The ajaxbridge integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, Event, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .client import AjaxbridgeClient
from .const import CONF_API_TOKEN, CONF_BRIDGE_URL, CONF_INSTALLATION_ID, DOMAIN, PLATFORMS
from .coordinator import AjaxbridgeCoordinator, AjaxbridgeData

_LOGGER = logging.getLogger(__name__)

SERVICE_UPDATE_ENTRY = "update_entry"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ajaxbridge from a config entry."""
    _async_register_services(hass)

    session = async_get_clientsession(hass)
    client = AjaxbridgeClient(
        session=session,
        bridge_url=entry.data[CONF_BRIDGE_URL],
        installation_id=entry.data[CONF_INSTALLATION_ID],
        api_token=entry.data[CONF_API_TOKEN],
    )
    coordinator = AjaxbridgeCoordinator(hass, client)
    coordinator.async_set_updated_data(AjaxbridgeData(installation_id=client.installation_id))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "ws_task": None,
        "refresh_task": None,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_start_background_tasks_after_startup(hass, entry, coordinator)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload ajaxbridge."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data and data.get("ws_task"):
        data["ws_task"].cancel()
    if data and data.get("refresh_task"):
        data["refresh_task"].cancel()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def _async_start_background_tasks_after_startup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Start long-running bridge tasks after HA startup wraps up."""

    def start_tasks(_: Event | None = None) -> None:
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if data is None:
            return
        if data.get("ws_task") is None:
            data["ws_task"] = hass.async_create_task(_ws_loop(coordinator))
        if data.get("refresh_task") is None:
            data["refresh_task"] = hass.async_create_task(
                _async_initial_refresh(hass, entry, coordinator)
            )

    if hass.state == CoreState.running:
        start_tasks()
        return

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, start_tasks)
    )


async def _async_initial_refresh(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Fetch the first state model without blocking HA startup."""
    try:
        await coordinator.async_refresh()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        _LOGGER.warning("Ajaxbridge initial refresh failed: %s", err)
        return

    _async_cleanup_registry(hass, entry, coordinator)


async def _ws_loop(coordinator: AjaxbridgeCoordinator) -> None:
    """Maintain the ajaxbridge WebSocket subscription."""
    while True:
        try:
            ws = await coordinator.client.connect_ws()
            coordinator.mark_ws_connected()
            await ws.send_json(
                {
                    "id": 1,
                    "type": "subscribe",
                    "streams": ["entity_state", "source_event", "availability"],
                }
            )
            async for message in ws:
                coordinator.mark_ws_message()
                if message.type != aiohttp.WSMsgType.TEXT:
                    continue
                payload = message.json()
                if payload.get("type") != "event":
                    continue
                coordinator.mark_ws_event()
                if payload.get("stream") == "entity_state":
                    coordinator.apply_entity_state(payload.get("event") or {})
        except asyncio.CancelledError:
            coordinator.mark_ws_disconnected("cancelled")
            raise
        except Exception as err:
            reason = _exception_reason(err)
            coordinator.mark_ws_disconnected(reason)
            if _should_log_ws_warning(err, reason):
                _LOGGER.warning("Ajaxbridge WebSocket disconnected: %s", reason)
            else:
                _LOGGER.debug("Ajaxbridge WebSocket disconnected: %s", reason)
            await asyncio.sleep(5)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register ajaxbridge maintenance services."""
    if hass.data.setdefault(DOMAIN, {}).get("_services_registered"):
        return

    async def update_entry(call: Any) -> None:
        entry_id = call.data["entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ValueError(f"Ajaxbridge config entry not found: {entry_id}")

        data = dict(entry.data)
        if CONF_BRIDGE_URL in call.data:
            data[CONF_BRIDGE_URL] = call.data[CONF_BRIDGE_URL].rstrip("/")
        if CONF_INSTALLATION_ID in call.data:
            data[CONF_INSTALLATION_ID] = call.data[CONF_INSTALLATION_ID].strip().lower()
        if CONF_API_TOKEN in call.data:
            data[CONF_API_TOKEN] = call.data[CONF_API_TOKEN]

        hass.config_entries.async_update_entry(entry, data=data)
        await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ENTRY,
        update_entry,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): str,
                vol.Optional(CONF_BRIDGE_URL): str,
                vol.Optional(CONF_INSTALLATION_ID): str,
                vol.Optional(CONF_API_TOKEN): str,
            }
        ),
    )
    hass.data[DOMAIN]["_services_registered"] = True


def _exception_reason(err: Exception) -> str:
    """Return a compact non-empty exception reason."""
    return str(err).strip() or err.__class__.__name__


def _should_log_ws_warning(err: Exception, reason: str) -> bool:
    """Return whether a WebSocket reconnect reason deserves warning-level logs."""
    if isinstance(err, TimeoutError):
        return False
    return reason not in {"TimeoutError", "ConnectionResetError"}


def _async_cleanup_registry(
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
