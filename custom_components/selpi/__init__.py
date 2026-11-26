"""Selectronic SP PRO via the selpi add-on.

The add-on owns the link to the inverter (Select.Live, serial, or TCP through the ESP proxy); this
integration only asks the add-on's API for values and turns them into a device with sensors.
"""
from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SelpiAuthError, SelpiClient, SelpiError
from .const import CONF_TOKEN, DOMAIN
from .esp import esp_active
from .coordinator import SelpiConfigEntry, SelpiCoordinator, SelpiRuntime

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]
# Default-enabled behaviour (which sensors are on, ESP-duplicate hiding, identity sensors off by default) comes
# from the add-on's field catalog `default` flag + the ESP check below; there is no cross-version migration.


async def async_setup_entry(hass: HomeAssistant, entry: SelpiConfigEntry) -> bool:
    client = SelpiClient(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT],
                         entry.data[CONF_TOKEN])
    try:
        info = await client.info()
        fields = await client.fields()
    except SelpiAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SelpiError as err:
        raise ConfigEntryNotReady(str(err)) from err
    esp = esp_active(entry, info)     # option if set, else auto-detected from the connection type (TCP = ESP proxy)
    units = info.get("units") or []
    multi = bool(info.get("multi"))
    if not multi:
        # ESP-duplicate hiding toggles the flat {prefix}_{key} sensors; a Powerchain's per-unit entities are new
        # ({prefix}_u<idx>_<key}) and the ESP doesn't publish multiphase yet, so this is single-inverter only.
        _apply_esp_present(hass, entry, fields, esp)
    _check_clock_conflict(hass, entry, esp, bool(info.get("clock_sync")))

    # split the default-enabled fields into the fast poll (the live power/volt/freq/SoC block, add-on `fast` flag)
    # and the slow poll (everything else). Each gets its own coordinator per unit; sensors attach to the matching
    # one. Keeping each screen's fields together on one coordinator avoids reading a block on both polls.
    default_fast = [f["key"] for f in fields if f.get("default") and f.get("fast")]
    default_slow = [f["key"] for f in fields if f.get("default") and not f.get("fast")]
    coordinators: dict = {}
    fast_coordinators: dict = {}
    if multi:
        real = [u for u in units if u["index"] != "system"]
        primary_index = real[0]["index"] if real else 0
        for u in units:                     # a slow + a fast coordinator per unit (incl. the synthetic "system")
            idx = u["index"]
            coordinators[idx] = SelpiCoordinator(hass, entry, client, info, default_slow,
                                                 unit=idx, fetch_diag=(idx == primary_index))
            fast_coordinators[idx] = SelpiCoordinator(hass, entry, client, info, default_fast,
                                                      unit=idx, fetch_diag=False, fast=True)
        coordinator = coordinators[primary_index]
    else:
        coordinator = SelpiCoordinator(hass, entry, client, info, default_slow)   # unit=None (primary/single)
        coordinators[None] = coordinator
        fast_coordinators[None] = SelpiCoordinator(hass, entry, client, info, default_fast, fetch_diag=False, fast=True)
    await coordinator.async_config_entry_first_refresh()   # gates setup; the primary carries the link diagnostics
    for c in (*coordinators.values(), *fast_coordinators.values()):   # the rest are best-effort (one flaky unit
        if c is not coordinator:                                      # or an empty fast set can't block setup)
            await c.async_refresh()
    entry.runtime_data = SelpiRuntime(client=client, info=info, fields=fields, coordinator=coordinator,
                                      coordinators=coordinators, fast_coordinators=fast_coordinators,
                                      units=units, multi=multi)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


CLOCK_CONFLICT_ISSUE = "esp_clock_conflict"


def _check_clock_conflict(hass: HomeAssistant, entry: SelpiConfigEntry, esp: bool, addon_clock_sync: bool) -> None:
    """The ESPHome component also syncs the SP PRO clock, so warn if the add-on is also syncing it."""
    if esp and addon_clock_sync:
        ir.async_create_issue(hass, DOMAIN, CLOCK_CONFLICT_ISSUE, is_fixable=False,
                              severity=ir.IssueSeverity.WARNING, translation_key=CLOCK_CONFLICT_ISSUE)
    else:
        ir.async_delete_issue(hass, DOMAIN, CLOCK_CONFLICT_ISSUE)


def _apply_esp_present(hass: HomeAssistant, entry: SelpiConfigEntry, fields: list, esp: bool) -> None:
    """When the ESP is present, the ESPHome component publishes the same SP PRO data, so disable the duplicate
    field sensors in the registry (so it also hides existing ones, not just new installs); re-enable the ones we
    disabled when it's no longer present. User-disabled entities are left alone.

    Only the *default* (normally-enabled) fields take part: the infrequently-used ones are disabled-by-default
    regardless of the ESP, and HA marks those with the same disabled_by=INTEGRATION, so touching them here would
    wrongly re-enable all of them when the ESP is absent."""
    reg = er.async_get(hass)
    prefix = entry.unique_id or entry.entry_id
    for f in fields:
        if not f.get("default"):
            continue
        eid = reg.async_get_entity_id("sensor", DOMAIN, f"{prefix}_{f['key']}")
        if eid is None:
            continue
        ent = reg.async_get(eid)
        if esp and ent and ent.disabled_by is None:
            reg.async_update_entity(eid, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
        elif not esp and ent and ent.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
            reg.async_update_entity(eid, disabled_by=None)


async def _options_updated(hass: HomeAssistant, entry: SelpiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SelpiConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
