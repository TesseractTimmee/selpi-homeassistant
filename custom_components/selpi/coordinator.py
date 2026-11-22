"""Polls the selpi add-on for the values of the enabled entities."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SelpiAuthError, SelpiClient, SelpiError
from .const import CONF_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Identity / factory values that never change: fetch once, then only rarely, instead of every poll — they
# otherwise add their registers to every cycle's link read for data that is constant.
STATIC_KEYS = frozenset({
    "version_number", "unit_model_number", "unit_serial_number",
    "control_pca_serial_number", "pm1_serial_number", "pm2_serial_number",
    # 0.6.0 factory/identity/firmware diagnostics — constant per unit, and all on the TechnicalDataSubTab block
    # (0xa015, 154 words); without this they pull that whole block every poll, which bogs down a Select.Live link.
    "factory_batteryless", "factory_export_limit", "comms_card_serial", "comms_card_software",
    "comms_card_stored_firmware", "grid_firmware", "comms_card_firmware_update",
    "kaco_mode", "number_of_kacos",
})
STATIC_EVERY = 60   # re-read the static values every N polls as a refresh (about hourly at a 60 s interval)
GRACE_FAILURES = 4  # keep the last values (marked stale) through this many consecutive failed polls before going
                    # unavailable — the add-on/link is often only briefly busy (a config read, a restart, Select.Live
                    # latency), and dropping every sensor on one failed HTTP call is the main cause of flapping.


@dataclass
class SelpiData:
    values: dict[str, Any] = field(default_factory=dict)
    stale: bool = False
    version_problems: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None     # a transient poll error while the last values are kept


type SelpiConfigEntry = ConfigEntry["SelpiRuntime"]


@dataclass
class SelpiRuntime:
    client: SelpiClient
    info: dict[str, Any]
    fields: list[dict[str, Any]]
    coordinator: "SelpiCoordinator"


class SelpiCoordinator(DataUpdateCoordinator[SelpiData]):
    """One request per poll for every enabled field; disabled entities cost nothing."""

    config_entry: SelpiConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SelpiConfigEntry, client: SelpiClient,
                 info: dict[str, Any], default_keys: list[str]) -> None:
        seconds = entry.options.get(CONF_SCAN_INTERVAL) or info.get("scan_interval") or 60
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN,
                         update_interval=timedelta(seconds=seconds))
        self.client = client
        self.keys: set[str] = set(default_keys)   # replaced by the entities that are actually added
        self._entity_keys: set[str] = set()
        self._warned_versions = False
        self._static: dict[str, Any] = {}          # cached values of the STATIC_KEYS (constant identity fields)
        self._cycle = 0
        self._fail_count = 0

    def add_key(self, key: str) -> bool:
        """An entity was added; True if its value hasn't been fetched yet."""
        if not self._entity_keys:
            self.keys = set()
        self._entity_keys.add(key)
        self.keys.add(key)
        return self.data is None or key not in self.data.values

    def remove_key(self, key: str) -> None:
        self._entity_keys.discard(key)
        self.keys.discard(key)

    async def _async_update_data(self) -> SelpiData:
        self._cycle += 1
        poll = set(self.keys)
        # once we have a static value cached, stop re-requesting it every poll (refresh occasionally)
        cached = STATIC_KEYS & self._static.keys()
        if cached and self._cycle % STATIC_EVERY != 0:
            poll -= cached
        try:
            got = await self.client.values(sorted(poll)) if poll else {"values": {}}
            diag = await self.client.diagnostics()
        except SelpiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SelpiError as err:
            self._fail_count += 1
            if self.data is not None and self._fail_count <= GRACE_FAILURES:
                _LOGGER.debug("selpi poll failed (%d/%d), keeping last values: %s",
                              self._fail_count, GRACE_FAILURES, err)
                return replace(self.data, stale=True, error=str(err))   # entities stay available (stale)
            raise UpdateFailed(str(err)) from err
        self._fail_count = 0
        problems = got.get("version_problems") or []
        if problems:
            # Same gate as the ESPHome component: the field table was verified at known firmware
            # versions only, so publish nothing rather than possibly wrong numbers.
            if not self._warned_versions:
                _LOGGER.warning("SP PRO firmware versions differ from those selpi was verified "
                                "against (%s); not publishing values", ", ".join(problems))
                self._warned_versions = True
            raise UpdateFailed("SP PRO versions not verified: " + ", ".join(problems))
        values = got.get("values") or {}
        for k in STATIC_KEYS:          # remember static values, and merge the cached ones back so those
            if values.get(k) is not None:   # sensors stay populated on the polls we skip re-reading them
                self._static[k] = values[k]
        for k, v in self._static.items():
            values.setdefault(k, v)
        return SelpiData(values=values, stale=bool(got.get("stale")),
                         version_problems=problems, diagnostics=diag)
