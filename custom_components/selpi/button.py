"""Buttons: back up settings (read-only to the SP PRO), and the SP PRO front panel buttons the app offers
(generator start/stop, silence alarm), pressed the way SP LINK's Quick View front panel does."""
from __future__ import annotations

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
    buttons = entry.runtime_data.info.get("buttons") or []
    async_add_entities([SelpiBackupButton(entry)] +
                       [SelpiPanelButton(entry, b) for b in buttons if b in PANEL_BUTTONS])


# front panel buttons the app may offer: key -> (name, icon)
PANEL_BUTTONS = {
    "generator": ("Generator start/stop", "mdi:engine"),
    "silence": ("Silence alarm", "mdi:volume-off"),
}


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
