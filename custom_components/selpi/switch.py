"""Switches that track the SP PRO's own state: the generator (Generator Status) and the inverter output
(Output Mode). Turning one on or off asks the app's state-aware control, which presses the front panel
button only when the unit's state needs it, so the switch can't toggle the wrong way. The state shown is
always the unit's, whatever started or stopped it (state of charge, schedule, remote input, front panel)."""
from __future__ import annotations

import time
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SelpiError
from .coordinator import SelpiConfigEntry
from .entity import SelpiEntity

IDLE_CONFIRM_SECONDS = 30


async def async_setup_entry(hass: HomeAssistant, entry: SelpiConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    controls = entry.runtime_data.info.get("controls") or []
    entities: list[SwitchEntity] = []
    if "generator" in controls:
        entities.append(SelpiGeneratorSwitch(entry))
    if "output" in controls:
        entities.append(SelpiOutputSwitch(entry))
    async_add_entities(entities)


class _StateSwitch(SelpiEntity, SwitchEntity):
    """A switch whose state is an SP PRO enum field (its label, as the app reports it)."""

    _state_key: str
    _control: str
    _on_labels: frozenset[str]
    _off_state: str

    def __init__(self, entry: SelpiConfigEntry, key: str) -> None:
        super().__init__(entry, key)
        self._client = entry.runtime_data.client

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.coordinator.add_key(self._state_key):
            await self.coordinator.async_request_refresh()

    async def async_will_remove_from_hass(self) -> None:
        self.coordinator.remove_key(self._state_key)
        await super().async_will_remove_from_hass()

    @property
    def _label(self) -> str | None:
        data = self.coordinator.data
        return data.values.get(self._state_key) if data else None

    @property
    def available(self) -> bool:
        return super().available and self._label is not None

    @property
    def is_on(self) -> bool | None:
        label = self._label
        return None if label is None else label in self._on_labels

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"sp_pro_state": self._label}

    async def _set(self, state: str, confirm: str | None = None) -> None:
        try:
            await self._client.control(self._control, state, confirm)
        except SelpiError as err:
            raise HomeAssistantError(f"{self.name}: {err}") from err
        await self.coordinator.async_request_refresh()   # pressed or not, show the unit's state

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set("on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(self._off_state)


class SelpiGeneratorSwitch(_StateSwitch):
    """On while the generator is starting or running. Turn on: start it (off grid; refused with the grid
    present, generator disabled / faulted / out of fuel). Turn off: stop it (skips the cool down)."""

    _state_key = "generator_status_from_led"
    _control = "generator"
    _on_labels = frozenset({"Running", "Starting"})
    _off_state = "off"
    _attr_icon = "mdi:engine"

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "control_generator")
        self._attr_name = "Generator"


class SelpiOutputSwitch(_StateSwitch):
    """Inverter AC output: on in On / Econo / Sync, off in Idle (no AC output: an outage).

    Protected like the old ON button: disabled until you enable it, and turning it off only asks for
    confirmation the first time ("turn off again within 30 s"); turning it on acts at once."""

    _state_key = "ac_out_status"
    _control = "output"
    _on_labels = frozenset({"On", "Econo", "Sync"})
    _off_state = "idle"
    _attr_icon = "mdi:power"
    # A control, not device configuration: shown in Controls. Kept safe by being disabled by default and needing
    # a second toggle-off within 30 s to actually idle the inverter.
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "control_output")
        self._attr_name = "Inverter output"
        self._asked_at = 0.0

    async def async_turn_off(self, **kwargs: Any) -> None:
        now = time.monotonic()
        if now - self._asked_at > IDLE_CONFIRM_SECONDS:
            self._asked_at = now
            raise HomeAssistantError(
                f"Turn off again within {IDLE_CONFIRM_SECONDS} s to put the inverter in IDLE. "
                "IDLE cuts the AC output (an outage)."
            )
        self._asked_at = 0.0
        await self._set("idle", confirm="outage")
