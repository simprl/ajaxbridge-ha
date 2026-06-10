"""Home Assistant services for Ajaxbridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN, CONF_BRIDGE_URL, CONF_INSTALLATION_ID, DOMAIN

SERVICE_UPDATE_ENTRY = "update_entry"


def async_register_services(hass: HomeAssistant) -> None:
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
