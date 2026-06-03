"""Config flow for ajaxbridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_API_TOKEN, CONF_BRIDGE_URL, CONF_INSTALLATION_ID, DOMAIN


class AjaxbridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an ajaxbridge config flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return AjaxbridgeOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            installation_id = user_input[CONF_INSTALLATION_ID].strip().lower()
            await self.async_set_unique_id(f"{DOMAIN}_{installation_id}")
            self._abort_if_unique_id_configured()

            data = {
                CONF_BRIDGE_URL: user_input[CONF_BRIDGE_URL].rstrip("/"),
                CONF_INSTALLATION_ID: installation_id,
                CONF_API_TOKEN: user_input[CONF_API_TOKEN],
            }
            return self.async_create_entry(title=f"Ajaxbridge {installation_id}", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BRIDGE_URL, default="https://ajaxbridge.ilazyhome.com"): str,
                    vol.Required(CONF_INSTALLATION_ID, default="site-prod"): str,
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )


class AjaxbridgeOptionsFlow(config_entries.OptionsFlow):
    """Handle ajaxbridge options updates."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage ajaxbridge connection settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            installation_id = user_input[CONF_INSTALLATION_ID].strip().lower()
            bridge_url = user_input[CONF_BRIDGE_URL].rstrip("/")
            data = {
                **self._config_entry.data,
                CONF_BRIDGE_URL: bridge_url,
                CONF_INSTALLATION_ID: installation_id,
                CONF_API_TOKEN: user_input[CONF_API_TOKEN],
            }
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                title=f"Ajaxbridge {installation_id}",
                data=data,
            )
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BRIDGE_URL,
                        default=self._config_entry.data.get(
                            CONF_BRIDGE_URL,
                            "https://ajaxbridge.ilazyhome.com",
                        ),
                    ): str,
                    vol.Required(
                        CONF_INSTALLATION_ID,
                        default=self._config_entry.data.get(CONF_INSTALLATION_ID, "site-prod"),
                    ): str,
                    vol.Required(
                        CONF_API_TOKEN,
                        default=self._config_entry.data.get(CONF_API_TOKEN, ""),
                    ): str,
                }
            ),
            errors=errors,
        )
