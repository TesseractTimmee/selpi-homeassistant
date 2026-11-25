"""Buttons: back up settings (read-only to the SP PRO), the SP PRO front panel buttons the app offers
(silence alarm; generator start/stop and ON/IDLE only from apps without state-aware controls, which are
switches now: switch.py), pressed the way SP LINK's Quick View front panel does, and the equalise request."""
from __future__ import annotations

import time

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SelpiError
from .coordinator import SelpiConfigEntry
from .entity import SelpiEntity


async def async_setup_entry(hass: HomeAssistant, entry: SelpiConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    info = entry.runtime_data.info
    buttons = info.get("buttons") or []
    controls = info.get("controls") or []
    entities: list[ButtonEntity] = [SelpiBackupButton(entry)]
    # with state-aware controls the generator and ON/IDLE are switches (switch.py), not toggling buttons
    entities += [SelpiPanelButton(entry, b) for b in buttons
                 if b in PANEL_BUTTONS and not (b == "generator" and "generator" in controls)]
    if "on" in buttons and "output" not in controls:
        entities.append(SelpiOnButton(entry))
    if "equalise" in controls:
        entities.append(SelpiEqualiseButton(entry))
    # Identify / flash front panel LEDs: per physical unit on a Powerchain (locate L1/L2/L3 boxes), one on the
    # main device for a single inverter. Benign momentary action (no passcode, no config change).
    if info.get("identify"):
        rt = entry.runtime_data
        real_units = [u for u in (rt.units or []) if u.get("index") != "system"]
        if rt.multi and real_units:
            entities += [SelpiIdentifyButton(entry, u["index"]) for u in real_units]
        else:
            entities.append(SelpiIdentifyButton(entry, None))
    async_add_entities(entities)


# front panel buttons the app may offer: key -> (name, icon)
PANEL_BUTTONS = {
    "generator": ("Generator start/stop", "mdi:engine"),
    "silence": ("Silence alarm", "mdi:volume-off"),
}


ON_CONFIRM_SECONDS = 30


class SelpiOnButton(SelpiEntity, ButtonEntity):
    """Long press of the SP PRO ON button: switches the inverter between ON and IDLE (IDLE = no AC output).

    Protected: disabled until you enable it, and the first press only asks for confirmation ("press again
    within 30 s"); the second press within 30 s acts. The app also refuses it without confirm=outage."""

    # A control, not device configuration: shown in the device's Controls (not Configuration). It stays safe by
    # being disabled by default and needing a second press within 30 s to act.
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:power"

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "panel_on")
        self._attr_name = "Inverter ON/IDLE (long press)"
        self._client = entry.runtime_data.client
        self._asked_at = 0.0

    async def async_press(self) -> None:
        now = time.monotonic()
        if now - self._asked_at > ON_CONFIRM_SECONDS:
            self._asked_at = now
            raise HomeAssistantError(
                f"Press again within {ON_CONFIRM_SECONDS} s to switch the inverter between ON and IDLE. "
                "IDLE cuts the AC output (an outage)."
            )
        self._asked_at = 0.0
        try:
            await self._client.press("on", confirm="outage")
        except SelpiError as err:
            raise HomeAssistantError(f"{self._attr_name}: {err}") from err
        await self.coordinator.async_request_refresh()


class SelpiPanelButton(SelpiEntity, ButtonEntity):
    """A short press of an SP PRO front panel button. Generator: starts or stops the auto start generator
    (off grid; on grid the SP PRO logs the press and does nothing)."""

    def __init__(self, entry: SelpiConfigEntry, button: str) -> None:
        super().__init__(entry, f"panel_{button}")
        self._button = button
        self._attr_name, self._attr_icon = PANEL_BUTTONS[button]
        self._client = entry.runtime_data.client

    async def async_press(self) -> None:
        try:
            await self._client.press(self._button)
        except SelpiError as err:
            raise HomeAssistantError(f"{self._attr_name}: {err}") from err
        await self.coordinator.async_request_refresh()


class SelpiEqualiseButton(SelpiEntity, ButtonEntity):
    """Request an equalise charge: two long presses of the Generator button (SP PRO manual). The SP PRO
    equalises after the next full charge; Days to Equalise / Days Since Equalise show the outcome."""

    _attr_icon = "mdi:battery-sync"

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "control_equalise")
        self._attr_name = "Request equalise"
        self._client = entry.runtime_data.client

    async def async_press(self) -> None:
        try:
            await self._client.control("equalise")
        except SelpiError as err:
            raise HomeAssistantError(f"{self._attr_name}: {err}") from err
        await self.coordinator.async_request_refresh()


class SelpiIdentifyButton(SelpiEntity, ButtonEntity):
    """Flash this inverter's front panel LEDs to locate it physically (SP LINK's double-click identify). On a
    Powerchain it re-addresses to the unit, flashes, and restores the link. A benign momentary action: no
    installer passcode and it changes no configuration, so it works ahead of settings write-enablement."""

    _attr_icon = "mdi:led-on"

    def __init__(self, entry: SelpiConfigEntry, unit) -> None:
        super().__init__(entry, "identify", unit=unit)
        self._attr_name = "Identify (flash LEDs)"
        self._unit = unit
        self._client = entry.runtime_data.client

    async def async_press(self) -> None:
        try:
            await self._client.identify(self._unit)
        except SelpiError as err:
            raise HomeAssistantError(f"{self._attr_name}: {err}") from err


class SelpiBackupButton(SelpiEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-save-cog"

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "backup_now")
        self._attr_name = "Back up settings"
        self._client = entry.runtime_data.client

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        try:
            result = await self._client.backup()
        except SelpiError as err:
            raise HomeAssistantError(str(err)) from err
        if not result.get("started"):
            raise HomeAssistantError(result.get("error") or "backup not started")
        await self.coordinator.async_request_refresh()
