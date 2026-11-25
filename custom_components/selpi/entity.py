"""Base entity. A single inverter is one "SP PRO" device; a Powerchain is a "SP PRO System" device (totals,
diagnostics, controls) with a sub-device per unit ("SP PRO L1 Manager", ...) nested under it."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ADDON_SLUG, DOMAIN
from .coordinator import SelpiConfigEntry, SelpiCoordinator


def device_info(entry: SelpiConfigEntry, unit: Any = None) -> DeviceInfo:
    """The device for an entity. unit None/"system" = the main device (the inverter, or the Powerchain System);
    a numeric unit index = that unit's sub-device, nested under the main device via via_device."""
    rt = entry.runtime_data
    info = rt.info
    slug = entry.data.get(CONF_ADDON_SLUG)
    prefix = entry.unique_id or entry.entry_id
    _model = info.get("model") or "SP PRO"
    _ratings = info.get("model_ratings")        # e.g. "48V DC, 7.5kW, 240V AC" - a model description, NOT a hw rev
    model = "%s (%s)" % (_model, _ratings) if _ratings else _model   # product string: "SPMC482 (48V DC, 7.5kW, 240V AC)"
    common = dict(manufacturer=info.get("manufacturer") or "Selectronic", model=model,
                  configuration_url=f"homeassistant://hassio/ingress/{slug}" if slug else None)
    if not rt.multi:
        hw = info.get("hw")
        return DeviceInfo(identifiers={(DOMAIN, prefix)}, name="SP PRO",
                          serial_number=info.get("serial"), sw_version=info.get("firmware"),
                          hw_version=(f"Rev {hw}" if hw is not None else None), **common)   # unit_rev_number
    if unit is None or unit == "system":
        return DeviceInfo(identifiers={(DOMAIN, prefix)}, name="SP PRO System", **common)
    u = next((x for x in rt.units if x["index"] == unit), {})
    return DeviceInfo(identifiers={(DOMAIN, f"{prefix}_u{unit}")}, name=f"SP PRO {u.get('label') or unit}",
                      serial_number=u.get("serial"), via_device=(DOMAIN, prefix), **common)


class SelpiEntity(CoordinatorEntity[SelpiCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry: SelpiConfigEntry, key: str, unit: Any = None,
                 coordinator: SelpiCoordinator | None = None) -> None:
        rt = entry.runtime_data
        super().__init__(coordinator or rt.coordinators.get(unit, rt.coordinator))
        prefix = entry.unique_id or entry.entry_id
        if rt.multi and unit is not None and unit != "system":
            self._attr_unique_id = f"{prefix}_u{unit}_{key}"
        elif rt.multi and unit == "system":
            self._attr_unique_id = f"{prefix}_system_{key}"
        else:
            self._attr_unique_id = f"{prefix}_{key}"      # single inverter, or the main device's own entities
        self._attr_device_info = device_info(entry, unit)
