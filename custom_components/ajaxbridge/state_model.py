"""Pure state-model helpers for the Ajaxbridge HA integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


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


def parse_state_model(state_model: dict[str, Any]) -> AjaxbridgeData:
    """Convert an ajaxbridge protocol state model into coordinator data."""
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


def object_id_from_entity_key(key: str) -> str | None:
    """Return a stable HA object id based on Ajax hub/group ids, not names."""
    parts = key.split(":")
    if len(parts) < 4 or parts[0] != "ajax":
        return None
    if parts[1] == "hub" and len(parts) >= 4:
        return _stable_object_id("ajax", parts[2], "_".join(parts[3:]))
    if parts[1] == "group" and len(parts) >= 5:
        suffix = "_".join(parts[4:])
        if suffix == "alarm":
            return _stable_object_id("ajax", parts[2], parts[3])
        return _stable_object_id("ajax", parts[2], parts[3], suffix)
    return None


def _stable_object_id(*parts: str) -> str:
    return re.sub(r"_+", "_", "_".join(_slug_part(part) for part in parts)).strip("_")


def _slug_part(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
