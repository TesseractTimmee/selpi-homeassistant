"""SP PRO sensors: every field selpi knows (the add-on's catalog), the default set enabled."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SelpiConfigEntry
from .entity import SelpiEntity
from .esp import esp_active

# selpi's units -> HA's spelling where they differ
UNITS = {"h": UnitOfTime.HOURS}


async def async_setup_entry(hass: HomeAssistant, entry: SelpiConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    # When the ESPHome component also runs it publishes the same SP PRO data, so hide these by default and keep only
    # the add-on-specific sensors (link, connection, backup) enabled; the user can still enable any they want.
    esp = esp_active(entry, entry.runtime_data.info)
    entities: list[SensorEntity] = [SelpiFieldSensor(entry, f, esp_present=esp) for f in entry.runtime_data.fields]
    entities += [SelpiLinkSensor(entry), SelpiConnectionSensor(entry),
                 SelpiClockDriftSensor(entry), SelpiLastBackupSensor(entry)]
    async_add_entities(entities)


class SelpiFieldSensor(SelpiEntity, SensorEntity):
    def __init__(self, entry: SelpiConfigEntry, f: dict[str, Any], esp_present: bool = False) -> None:
        super().__init__(entry, f["key"])
        self._key = f["key"]
        self._attr_name = f["name"]
        self._attr_entity_registry_enabled_default = bool(f.get("default")) and not esp_present
        if f.get("device_class"):
            self._attr_device_class = SensorDeviceClass(f["device_class"])
        if f.get("state_class"):
            self._attr_state_class = SensorStateClass(f["state_class"])
        if f.get("unit"):
            self._attr_native_unit_of_measurement = UNITS.get(f["unit"], f["unit"])
        if f.get("precision") is not None:
            self._attr_suggested_display_precision = f["precision"]
        if f.get("category") == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._options = list(f.get("options") or [])
        self._note = f.get("note") or ""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.coordinator.add_key(self._key):
            await self.coordinator.async_request_refresh()

    async def async_will_remove_from_hass(self) -> None:
        self.coordinator.remove_key(self._key)
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None \
            and self._key in self.coordinator.data.values

    @property
    def options(self) -> list[str] | None:
        if self.device_class != SensorDeviceClass.ENUM:
            return None
        value = self.native_value
        # a code SP LINK's tables don't know comes through as "code N": accept it rather than fail
        return self._options + [value] if isinstance(value, str) and value not in self._options else self._options

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        return data.values.get(self._key) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attrs: dict[str, Any] = {}
        if self._note:
            attrs["note"] = self._note
        if self.coordinator.data and self.coordinator.data.stale:
            attrs["stale"] = True
        return attrs or None


class _Diag(SelpiEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: SelpiConfigEntry, key: str, name: str) -> None:
        super().__init__(entry, key)
        self._attr_name = name

    @property
    def _diag(self) -> dict[str, Any]:
        return (self.coordinator.data.diagnostics if self.coordinator.data else None) or {}


class SelpiLinkSensor(_Diag):
    """OK, busy (what holds the link), or the last error."""

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "link_status", "Link status")
        self._attr_icon = "mdi:lan-connect"

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        if not self.coordinator.last_update_success:
            err = str(self.coordinator.last_exception or "add-on not reachable")
            return err[:255]
        data = self.coordinator.data
        d = self._diag
        if d.get("link_down"):           # breaker tripped: repeated reconnect failures (e.g. Select.Live session held)
            return f"reconnecting: {d.get('last_error') or 'link down'}"[:255]
        if data and data.error:          # a poll failed but the last values are being kept (grace period)
            return f"retrying: {data.error}"[:255]
        if d.get("last_error"):
            return str(d["last_error"])[:255]
        if data and data.stale:
            return f"busy: {d.get('busy') or 'link in use'}"[:255]
        return "OK"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self._diag
        return {"connection": self.coordinator.config_entry.runtime_data.info.get("connection"),
                "last_ok": d.get("last_ok"),
                "versions": self.coordinator.config_entry.runtime_data.info.get("versions")}


class SelpiConnectionSensor(_Diag):
    """How the add-on reaches the SP PRO: Serial, TCP, Select.Live or Select.Live 2."""

    _attr_icon = "mdi:transit-connection-variant"

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "connected_via", "Connected via")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str | None:
        info = self.coordinator.config_entry.runtime_data.info
        return info.get("connection_label") or info.get("connection") or None


class SelpiClockDriftSensor(_Diag):
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:clock-alert-outline"

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "clock_drift", "Clock drift")

    @property
    def available(self) -> bool:
        return super().available and self._diag.get("clock", {}).get("drift") is not None

    @property
    def native_value(self) -> int | None:
        return self._diag.get("clock", {}).get("drift")


class SelpiLastBackupSensor(_Diag):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: SelpiConfigEntry) -> None:
        super().__init__(entry, "last_backup", "Last config backup")

    @property
    def native_value(self):
        at = (self._diag.get("last_backup") or {}).get("at")
        return dt_util.parse_datetime(at) if at else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        last = self._diag.get("last_backup")
        return {"name": last.get("name"), "reason": last.get("reason")} if last else None
