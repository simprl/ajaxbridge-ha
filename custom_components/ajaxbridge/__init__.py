"""The ajaxbridge integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AjaxbridgeClient
from .const import CONF_API_TOKEN, CONF_BRIDGE_URL, CONF_INSTALLATION_ID, DOMAIN, PLATFORMS
from .coordinator import AjaxbridgeCoordinator

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
    await coordinator.async_config_entry_first_refresh()

    ws_task = hass.async_create_task(_ws_loop(coordinator))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "ws_task": ws_task,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload ajaxbridge."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data and data.get("ws_task"):
        data["ws_task"].cancel()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


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
            coordinator.mark_ws_disconnected(str(err))
            _LOGGER.warning("Ajaxbridge WebSocket disconnected: %s", err)
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
