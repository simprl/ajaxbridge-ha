"""Pure helpers for Ajaxbridge config and options flows."""

from __future__ import annotations

from typing import Any, NamedTuple


class ConnectionSettings(NamedTuple):
    """Normalized Ajaxbridge connection settings from a HA form."""

    bridge_url: str
    installation_id: str
    api_token: str


def normalize_connection_settings(user_input: dict[str, Any]) -> ConnectionSettings:
    """Normalize connection settings submitted by Home Assistant forms."""
    return ConnectionSettings(
        bridge_url=str(user_input["bridge_url"]).strip().rstrip("/"),
        installation_id=str(user_input["installation_id"]).strip().lower(),
        api_token=str(user_input["api_token"]).strip(),
    )


def flow_error_from_api_status(status: int, detail: str) -> str:
    """Map ajaxbridge API status/detail values to Home Assistant error keys."""
    if detail == "max_hubs_exceeded":
        return "max_hubs_exceeded"
    if status in (401, 403):
        return "unauthorized"
    if status == 404:
        return "not_found"
    if status == 409:
        return "conflict"
    return "request_failed"


def membership_change_key(membership: dict[str, Any]) -> str:
    """Return the option key for a membership enable/disable action."""
    action = "disable" if membership.get("enabled") else "enable"
    return f"{action}:{membership['membership_id']}"


def membership_change_label(membership: dict[str, Any]) -> str:
    """Return the option label for a membership enable/disable action."""
    action = "Disable" if membership.get("enabled") else "Enable"
    state = "enabled" if membership.get("enabled") else "disabled"
    hub_id = str(membership["hub_id"])
    name = str(membership.get("hub_name") or hub_id)
    model = str(membership.get("hub_model") or "").strip()
    details = hub_id
    if model and model.lower() != "ajax hub":
        details = f"{details}, {model}"
    return f"{action} {name} ({details}) / {state}"


def capacity_text(installation: dict[str, Any]) -> str:
    """Return a compact installation capacity summary for HA forms."""
    available = int(installation.get("available_slots") or 0)
    max_hubs = int(installation.get("max_hubs") or 0)
    enabled = int(installation.get("enabled_count") or 0)
    disabled = int(installation.get("disabled_count") or 0)
    return f"available={available}/{max_hubs}; enabled={enabled}; disabled={disabled}"
