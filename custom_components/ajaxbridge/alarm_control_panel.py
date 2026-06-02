"""Alarm control panel platform for ajaxbridge."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AjaxbridgeCoordinator
from .entity import AjaxbridgeEntity, setup_dynamic_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up alarm panels from the state model."""
    coordinator: AjaxbridgeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    setup_dynamic_entities(
        entry,
        coordinator,
        async_add_entities,
        "alarm_control_panel",
        AjaxbridgeAlarmControlPanel,
    )


class AjaxbridgeAlarmControlPanel(AjaxbridgeEntity, AlarmControlPanelEntity):
    """Ajaxbridge alarm panel."""

    _attr_has_entity_name = False
    _attr_supported_features = AlarmControlPanelEntityFeature(0)
    _attr_code_arm_required = False

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return no supported control actions for read-only Ajax state."""
        return AlarmControlPanelEntityFeature(0)

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the alarm state."""
        state = self.entity_data.state
        if state == "armed_away":
            return AlarmControlPanelState.ARMED_AWAY
        if state == "armed_home":
            return AlarmControlPanelState.ARMED_HOME
        if state == "armed_night":
            return AlarmControlPanelState.ARMED_NIGHT
        if state == "arming":
            return AlarmControlPanelState.ARMING
        if state == "triggered":
            return AlarmControlPanelState.TRIGGERED
        if state == "unknown":
            return None
        return AlarmControlPanelState.DISARMED
