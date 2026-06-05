"""Config flow for ajaxbridge."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AjaxbridgeApiError, AjaxbridgeClient
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
            bridge_url = user_input[CONF_BRIDGE_URL].rstrip("/")
            api_token = user_input[CONF_API_TOKEN].strip()

            if not api_token:
                errors[CONF_API_TOKEN] = "required"
            else:
                validation_error = await _validate_connection_settings(
                    hass=self.hass,
                    bridge_url=bridge_url,
                    installation_id=installation_id,
                    api_token=api_token,
                )
                if validation_error:
                    errors["base"] = validation_error
                else:
                    await self.async_set_unique_id(f"{DOMAIN}_{installation_id}")
                    self._abort_if_unique_id_configured()

                    data = {
                        CONF_BRIDGE_URL: bridge_url,
                        CONF_INSTALLATION_ID: installation_id,
                        CONF_API_TOKEN: api_token,
                    }
                    return self.async_create_entry(
                        title=f"Ajaxbridge {installation_id}",
                        data=data,
                    )

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
        return self.async_show_menu(
            step_id="init",
            menu_options=[ACTION_ADD_HUB, ACTION_MEMBERSHIPS, ACTION_CONNECTION],
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
                validation_error = await _validate_connection_settings(
                    hass=self.hass,
                    bridge_url=bridge_url,
                    installation_id=installation_id,
                    api_token=api_token,
                )
                if validation_error:
                    errors["base"] = validation_error
                else:
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
            except AjaxbridgeApiError as err:
                errors["base"] = _flow_error_from_api(err)
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
            except AjaxbridgeApiError as err:
                errors["base"] = _flow_error_from_api(err)
            except (aiohttp.ClientError, RuntimeError):
                errors["base"] = "request_failed"
            else:
                self._claim = response["claim"]
                if self._claim["status"] == "verified":
                    return await self.async_step_complete_claim()
                if self._claim["status"] == "expired":
                    errors["base"] = "expired"
                else:
                    errors["base"] = "not_verified"

        return self.async_show_form(
            step_id="verify_hub",
            data_schema=vol.Schema(
                {
                    vol.Optional("verification_code", default=claim["code"]): str,
                    vol.Optional("hub_id", default=claim["hub_id"]): str,
                }
            ),
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
            if not user_input.get("confirm_complete"):
                errors["base"] = "required"
            else:
                try:
                    await self._client().complete_claim(claim["claim_id"])
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                except AjaxbridgeApiError as err:
                    errors["base"] = _flow_error_from_api(err)
                except (aiohttp.ClientError, RuntimeError):
                    errors["base"] = "request_failed"
                else:
                    return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="complete_claim",
            data_schema=vol.Schema(
                {
                    vol.Optional("hub_id", default=claim["hub_id"]): str,
                    vol.Required("confirm_complete", default=True): bool,
                }
            ),
            description_placeholders={
                "hub_id": claim["hub_id"],
                "capacity": await self._capacity_text(),
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
        except AjaxbridgeApiError as err:
            return self.async_show_form(
                step_id="memberships",
                data_schema=vol.Schema({}),
                errors={"base": _flow_error_from_api(err)},
            )
        except (aiohttp.ClientError, RuntimeError):
            return self.async_show_form(
                step_id="memberships",
                data_schema=vol.Schema({}),
                errors={"base": "request_failed"},
            )
        memberships = response.get("memberships") or []
        membership_by_change = {
            _membership_change_key(item): item
            for item in memberships
        }
        choices = {
            change_key: _membership_change_label(item)
            for change_key, item in membership_by_change.items()
        }
        if not choices:
            return self.async_show_form(
                step_id="memberships",
                data_schema=vol.Schema({}),
                errors={"base": "no_memberships"},
            )

        if user_input is not None:
            change_key = user_input["membership_change"]
            membership = membership_by_change[change_key]
            try:
                if membership.get("enabled"):
                    await self._client().disable_membership(membership["membership_id"])
                else:
                    await self._client().enable_membership(membership["membership_id"])
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            except AjaxbridgeApiError as err:
                errors["base"] = _flow_error_from_api(err)
            except (aiohttp.ClientError, RuntimeError):
                errors["base"] = "request_failed"
            else:
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="memberships",
            data_schema=vol.Schema(
                {
                    vol.Required("membership_change"): vol.In(choices),
                }
            ),
            description_placeholders={
                "capacity": await self._capacity_text(),
            },
            errors=errors,
        )

    def _client(self) -> AjaxbridgeClient:
        return AjaxbridgeClient(
            session=async_get_clientsession(self.hass),
            bridge_url=self.config_entry.data[CONF_BRIDGE_URL],
            installation_id=self.config_entry.data[CONF_INSTALLATION_ID],
            api_token=self.config_entry.data[CONF_API_TOKEN],
        )

    async def _capacity_text(self) -> str:
        try:
            response = await self._client().get_installation()
        except (AjaxbridgeApiError, aiohttp.ClientError, RuntimeError):
            return "capacity unavailable"
        installation = response.get("installation") or {}
        return _capacity_text(installation)


def _flow_error_from_api(err: AjaxbridgeApiError) -> str:
    """Map ajaxbridge API errors to Home Assistant translation keys."""
    if err.detail == "max_hubs_exceeded":
        return "max_hubs_exceeded"
    if err.status in (401, 403):
        return "unauthorized"
    if err.status == 404:
        return "not_found"
    if err.status == 409:
        return "conflict"
    return "request_failed"


async def _validate_connection_settings(
    *,
    hass: Any,
    bridge_url: str,
    installation_id: str,
    api_token: str,
) -> str | None:
    """Validate that the token authenticates as the requested installation."""
    client = AjaxbridgeClient(
        session=async_get_clientsession(hass),
        bridge_url=bridge_url,
        installation_id=installation_id,
        api_token=api_token,
    )
    try:
        response = await client.get_installation()
    except AjaxbridgeApiError as err:
        return _flow_error_from_api(err)
    except (aiohttp.ClientError, RuntimeError):
        return "request_failed"

    installation = response.get("installation") or {}
    actual_installation_id = str(installation.get("installation_id") or "").strip().lower()
    if actual_installation_id != installation_id:
        return "installation_mismatch"
    return None


def _membership_change_key(membership: dict[str, Any]) -> str:
    action = "disable" if membership.get("enabled") else "enable"
    return f"{action}:{membership['membership_id']}"


def _membership_change_label(membership: dict[str, Any]) -> str:
    action = "Disable" if membership.get("enabled") else "Enable"
    state = "enabled" if membership.get("enabled") else "disabled"
    hub_id = str(membership["hub_id"])
    name = str(membership.get("hub_name") or hub_id)
    model = str(membership.get("hub_model") or "").strip()
    details = hub_id
    if model and model.lower() != "ajax hub":
        details = f"{details}, {model}"
    return f"{action} {name} ({details}) / {state}"


def _capacity_text(installation: dict[str, Any]) -> str:
    available = int(installation.get("available_slots") or 0)
    max_hubs = int(installation.get("max_hubs") or 0)
    enabled = int(installation.get("enabled_count") or 0)
    disabled = int(installation.get("disabled_count") or 0)
    return f"available={available}/{max_hubs}; enabled={enabled}; disabled={disabled}"
