"""The ajaxbridge integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, Event, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AjaxbridgeClient
from .const import CONF_API_TOKEN, CONF_BRIDGE_URL, CONF_INSTALLATION_ID, DOMAIN, PLATFORMS
from .coordinator import AjaxbridgeCoordinator
from .registry import (
    async_align_group_entity_ids,
    async_cleanup_registry,
    async_delayed_align_group_entity_ids,
)
from .services import async_register_services
from .state_model import AjaxbridgeData
from .websocket import ws_loop

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ajaxbridge from a config entry."""
    async_register_services(hass)

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
        "tasks": set(),
        "ws_task": None,
        "refresh_task": None,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_start_background_tasks_after_startup(hass, entry, coordinator)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload ajaxbridge."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    if data:
        await _async_cancel_entry_tasks(data)
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_start_background_tasks_after_startup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AjaxbridgeCoordinator,
) -> None:
    """Start long-running bridge tasks after HA startup wraps up."""

    async def start_tasks(_: Event | None = None) -> None:
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if data is None:
            return
        if data.get("ws_task") is None:
            data["ws_task"] = _async_create_entry_task(
                hass,
                data,
                ws_loop(coordinator),
                "ajaxbridge websocket",
            )
        if data.get("refresh_task") is None:
            data["refresh_task"] = _async_create_entry_task(
                hass,
                data,
                _async_initial_refresh(hass, entry, coordinator),
                "ajaxbridge initial refresh",
            )

    if hass.state == CoreState.running:
        await start_tasks()
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

    async_cleanup_registry(hass, entry, coordinator)
    async_align_group_entity_ids(hass, entry, coordinator)
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data is None:
        return
    _async_create_entry_task(
        hass,
        data,
        async_delayed_align_group_entity_ids(hass, entry, coordinator),
        "ajaxbridge align group entity ids",
    )


def _async_create_entry_task(
    hass: HomeAssistant,
    data: dict[str, Any],
    coro: Coroutine[Any, Any, Any],
    name: str,
) -> asyncio.Task:
    """Create and track a config-entry scoped background task."""
    task = hass.async_create_background_task(coro, name)
    tasks: set[asyncio.Task] = data.setdefault("tasks", set())
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return task


async def _async_cancel_entry_tasks(data: dict[str, Any]) -> None:
    """Cancel and await all config-entry scoped background tasks."""
    tasks = set(data.get("tasks") or ())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
