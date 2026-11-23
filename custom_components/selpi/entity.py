"""Base entity: one device per SP PRO."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ADDON_SLUG, DOMAIN
from .coordinator import SelpiConfigEntry, SelpiCoordinator


def device_info(entry: SelpiConfigEntry) -> DeviceInfo:
    info = entry.runtime_data.info
    slug = entry.data.get(CONF_ADDON_SLUG)
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer=info.get("manufacturer") or "Selectronic",
        model=info.get("model") or "SP PRO",
        name="SP PRO",
        serial_number=info.get("serial"),
        sw_version=info.get("firmware"),
        configuration_url=f"homeassistant://hassio/ingress/{slug}" if slug else None,
    )


class SelpiEntity(CoordinatorEntity[SelpiCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry: SelpiConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)
