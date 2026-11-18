"""Backup now: the add-on reads every setting and saves a backup (SPLC + CSV). Read-only to the SP PRO."""
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
    async_add_entities([SelpiBackupButton(entry)])


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
