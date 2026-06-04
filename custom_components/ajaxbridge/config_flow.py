"""Config flow for ajaxbridge."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AjaxbridgeClient
from .const import CONF_API_TOKEN, CONF_BRIDGE_URL, CONF_INSTALLATION_ID, DOMAIN

ACTION_ADD_HUB = "add_hub"
ACTION_CONNECTION = "connection"
ACTION_MEMBERSHIPS = "memberships"


class AjaxbridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an ajaxbridge config flow."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return AjaxbridgeOptionsFlow()

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

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show ajaxbridge options menu."""
        if user_input is not None:
            action = user_input["action"]
            if action == ACTION_ADD_HUB:
                return await self.async_step_add_hub()
            if action == ACTION_MEMBERSHIPS:
                return await self.async_step_memberships()
            return await self.async_step_connection()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default=ACTION_ADD_HUB): vol.In(
                        {
                            ACTION_ADD_HUB: "Add hub",
                            ACTION_MEMBERSHIPS: "Enable/disable membership",
                            ACTION_CONNECTION: "Connection settings",
                        }
                    ),
                }
            ),
        )

    async def async_step_connection(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage ajaxbridge connection settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_token = user_input[CONF_API_TOKEN].strip()
            if not api_token:
                errors[CONF_API_TOKEN] = "required"
            else:
                installation_id = user_input[CONF_INSTALLATION_ID].strip().lower()
                bridge_url = user_input[CONF_BRIDGE_URL].rstrip("/")
                data = {
                    **self.config_entry.data,
                    CONF_BRIDGE_URL: bridge_url,
                    CONF_INSTALLATION_ID: installation_id,
                    CONF_API_TOKEN: api_token,
                }
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=f"Ajaxbridge {installation_id}",
                    data=data,
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BRIDGE_URL,
                        default=self.config_entry.data.get(
                            CONF_BRIDGE_URL,
                            "https://ajaxbridge.ilazyhome.com",
                        ),
                    ): str,
                    vol.Required(
                        CONF_INSTALLATION_ID,
                        default=self.config_entry.data.get(CONF_INSTALLATION_ID, "site-prod"),
                    ): str,
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_add_hub(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Create a hub claim."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                response = await self._client().create_claim(
                    hub_id=user_input["hub_id"].strip(),
                    hub_name=(user_input.get("hub_name") or "").strip() or None,
                    hub_model=(user_input.get("hub_model") or "").strip() or None,
                )
            except (aiohttp.ClientError, RuntimeError):
                errors["base"] = "request_failed"
            else:
                self._claim = response["claim"]
                return await self.async_step_verify_hub()

        return self.async_show_form(
            step_id="add_hub",
            data_schema=vol.Schema(
                {
                    vol.Required("hub_id"): str,
                    vol.Optional("hub_name"): str,
                    vol.Optional("hub_model"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_verify_hub(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Verify a hub claim."""
        errors: dict[str, str] = {}
        claim = getattr(self, "_claim", None)
        if not claim:
            return await self.async_step_add_hub()

        if user_input is not None:
            try:
                response = await self._client().verify_claim(claim["claim_id"])
            except (aiohttp.ClientError, RuntimeError):
                errors["base"] = "request_failed"
            else:
                self._claim = response["claim"]
                if self._claim["status"] == "verified":
                    return await self.async_step_complete_claim()
                errors["base"] = "not_verified"

        return self.async_show_form(
            step_id="verify_hub",
            data_schema=vol.Schema({}),
            description_placeholders={
                "hub_id": claim["hub_id"],
                "code": claim["code"],
            },
            errors=errors,
        )

    async def async_step_complete_claim(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Complete a verified claim."""
        errors: dict[str, str] = {}
        claim = getattr(self, "_claim", None)
        if not claim:
            return await self.async_step_add_hub()

        if user_input is not None:
            try:
                await self._client().complete_claim(claim["claim_id"])
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            except (aiohttp.ClientError, RuntimeError):
                errors["base"] = "request_failed"
            else:
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="complete_claim",
            data_schema=vol.Schema({}),
            description_placeholders={
                "hub_id": claim["hub_id"],
            },
            errors=errors,
        )

    async def async_step_memberships(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Enable or disable an existing membership."""
        errors: dict[str, str] = {}
        try:
            response = await self._client().list_memberships()
        except (aiohttp.ClientError, RuntimeError):
            return self.async_show_form(
                step_id="memberships",
                data_schema=vol.Schema({}),
                errors={"base": "request_failed"},
            )
        memberships = response.get("memberships") or []
        choices = {
            item["membership_id"]: (
                f"{item.get('hub_name') or item['hub_id']} / "
                f"{'enabled' if item.get('enabled') else 'disabled'}"
            )
            for item in memberships
        }
        if not choices:
            return self.async_show_form(
                step_id="memberships",
                data_schema=vol.Schema({}),
                errors={"base": "no_memberships"},
            )

        if user_input is not None:
            try:
                if user_input["membership_action"] == "enable":
                    await self._client().enable_membership(user_input["membership_id"])
                else:
                    await self._client().disable_membership(user_input["membership_id"])
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            except (aiohttp.ClientError, RuntimeError):
                errors["base"] = "request_failed"
            else:
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="memberships",
            data_schema=vol.Schema(
                {
                    vol.Required("membership_id"): vol.In(choices),
                    vol.Required("membership_action", default="enable"): vol.In(
                        {
                            "enable": "Enable membership",
                            "disable": "Disable membership",
                        }
                    ),
                }
            ),
            errors=errors,
        )

    def _client(self) -> AjaxbridgeClient:
        return AjaxbridgeClient(
            session=async_get_clientsession(self.hass),
            bridge_url=self.config_entry.data[CONF_BRIDGE_URL],
            installation_id=self.config_entry.data[CONF_INSTALLATION_ID],
            api_token=self.config_entry.data[CONF_API_TOKEN],
        )
