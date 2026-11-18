"""Polls the selpi add-on for the values of the enabled entities."""
from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class SelpiData:
    values: dict[str, Any] = field(default_factory=dict)
    stale: bool = False
    version_problems: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


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
        try:
            got = await self.client.values(sorted(self.keys)) if self.keys else {"values": {}}
            diag = await self.client.diagnostics()
        except SelpiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SelpiError as err:
            raise UpdateFailed(str(err)) from err
        problems = got.get("version_problems") or []
        if problems:
            # Same gate as the ESPHome component: the field table was verified at known firmware
            # versions only, so publish nothing rather than possibly wrong numbers.
            if not self._warned_versions:
                _LOGGER.warning("SP PRO firmware versions differ from those selpi was verified "
                                "against (%s); not publishing values", ", ".join(problems))
                self._warned_versions = True
            raise UpdateFailed("SP PRO versions not verified: " + ", ".join(problems))
        return SelpiData(values=got.get("values") or {}, stale=bool(got.get("stale")),
                         version_problems=problems, diagnostics=diag)
