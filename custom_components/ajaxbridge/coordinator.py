"""Coordinator for ajaxbridge entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AjaxbridgeClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class AjaxbridgeEntityDescription:
    """Entity definition received from ajaxbridge."""

    key: str
    platform: str
    name: str
    device_key: str | None = None
    state: Any = None
    available: bool = True
    device_class: str | None = None
    capabilities: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class AjaxbridgeData:
    """Current state model data."""

    installation_id: str
    devices: dict[str, dict[str, Any]] = field(default_factory=dict)
    entities: dict[str, AjaxbridgeEntityDescription] = field(default_factory=dict)


class AjaxbridgeCoordinator(DataUpdateCoordinator[AjaxbridgeData]):
    """Manage ajaxbridge data."""

    def __init__(self, hass: HomeAssistant, client: AjaxbridgeClient) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=1))
        self.client = client
        self.ws_connected = False
        self.ws_connects = 0
        self.ws_disconnects = 0
        self.ws_messages = 0
        self.ws_events = 0
        self.ws_entity_state_events = 0
        self.ws_entity_state_applied = 0
        self.ws_entity_state_ignored = 0
        self.ws_last_connected_at: str | None = None
        self.ws_last_message_at: str | None = None
        self.ws_last_event_at: str | None = None
        self.ws_last_entity_key: str | None = None
        self.ws_last_error: str | None = None
        self.rest_refreshes = 0
        self.rest_last_refresh_at: str | None = None
        self.rest_last_state_seq: int | None = None

    async def _async_update_data(self) -> AjaxbridgeData:
        try:
            state_model = await self.client.get_state_model()
        except Exception as err:
            raise UpdateFailed(f"Error fetching ajaxbridge state model: {err}") from err

        self.rest_refreshes += 1
        self.rest_last_refresh_at = _utc_now_iso()
        self.rest_last_state_seq = state_model.get("state_seq")
        devices = {device["key"]: device for device in state_model.get("devices", [])}
        entities = {
            entity["key"]: AjaxbridgeEntityDescription(**entity)
            for entity in state_model.get("entities", [])
        }
        return AjaxbridgeData(
            installation_id=state_model["installation_id"],
            devices=devices,
            entities=entities,
        )

    def apply_entity_state(self, event: dict[str, Any]) -> None:
        """Apply an entity_state event from the WebSocket stream."""
        self.ws_entity_state_events += 1
        self.ws_last_event_at = _utc_now_iso()
        if not self.data:
            self.ws_entity_state_ignored += 1
            return
        entity_key = event.get("entity_key")
        if not entity_key or entity_key not in self.data.entities:
            self.ws_entity_state_ignored += 1
            return
        entity = self.data.entities[entity_key]
        entity.state = event.get("state")
        entity.available = bool(event.get("available", True))
        entity.attributes.update(event.get("attributes") or {})
        self.ws_entity_state_applied += 1
        self.ws_last_entity_key = entity_key
        self.async_set_updated_data(self.data)

    def mark_ws_connected(self) -> None:
        """Record WebSocket connection."""
        self.ws_connected = True
        self.ws_connects += 1
        self.ws_last_connected_at = _utc_now_iso()
        self.ws_last_error = None

    def mark_ws_message(self) -> None:
        """Record WebSocket message."""
        self.ws_messages += 1
        self.ws_last_message_at = _utc_now_iso()

    def mark_ws_event(self) -> None:
        """Record WebSocket event."""
        self.ws_events += 1
        self.ws_last_event_at = _utc_now_iso()

    def mark_ws_disconnected(self, error: str | None = None) -> None:
        """Record WebSocket disconnect."""
        self.ws_connected = False
        self.ws_disconnects += 1
        if error:
            self.ws_last_error = error

    def diagnostics(self) -> dict[str, Any]:
        """Return HA-side ajaxbridge diagnostics."""
        return {
            "ws_connected": self.ws_connected,
            "ws_connects": self.ws_connects,
            "ws_disconnects": self.ws_disconnects,
            "ws_messages": self.ws_messages,
            "ws_events": self.ws_events,
            "ws_entity_state_events": self.ws_entity_state_events,
            "ws_entity_state_applied": self.ws_entity_state_applied,
            "ws_entity_state_ignored": self.ws_entity_state_ignored,
            "ws_last_connected_at": self.ws_last_connected_at,
            "ws_last_message_at": self.ws_last_message_at,
            "ws_last_event_at": self.ws_last_event_at,
            "ws_last_entity_key": self.ws_last_entity_key,
            "ws_last_error": self.ws_last_error,
            "rest_refreshes": self.rest_refreshes,
            "rest_last_refresh_at": self.rest_last_refresh_at,
            "rest_last_state_seq": self.rest_last_state_seq,
        }


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
