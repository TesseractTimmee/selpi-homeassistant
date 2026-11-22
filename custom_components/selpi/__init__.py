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
# field keys renamed in selpi 0.4.7 (SP LINK's "DaystoEqualise" split badly): keep the entities
RENAMED_KEYS = {"daysto_recharge": "days_to_recharge", "daysto_equalise": "days_to_equalise"}
NONDEFAULT_REPAIRED = "nondefault_repaired"   # one-time flag: the 0.6.0 re-enable-all bug has been undone


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
    _migrate_renamed_keys(hass, entry, {f["key"] for f in fields})
    esp = esp_active(entry, info)     # option if set, else auto-detected from the connection type (TCP = ESP proxy)
    _apply_esp_present(hass, entry, fields, esp)
    _repair_nondefault_enabled(hass, entry, fields)
    _check_clock_conflict(hass, entry, esp, bool(info.get("clock_sync")))
    coordinator = SelpiCoordinator(hass, entry, client, info, [f["key"] for f in fields if f.get("default")])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = SelpiRuntime(client=client, info=info, fields=fields, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


def _migrate_renamed_keys(hass: HomeAssistant, entry: SelpiConfigEntry, keys: set[str]) -> None:
    """Move sensors from renamed field keys to the new ones, keeping entity id and history. If the app was
    updated first, an older integration may already have made a second entity for the new key (e.g.
    sensor.sp_pro_days_to_equalise_2): that duplicate is removed so the original takes its key."""
    reg = er.async_get(hass)
    prefix = entry.unique_id or entry.entry_id
    for old, new in RENAMED_KEYS.items():
        if new not in keys:
            continue
        old_id = reg.async_get_entity_id("sensor", DOMAIN, f"{prefix}_{old}")
        if old_id is None:
            continue
        dup = reg.async_get_entity_id("sensor", DOMAIN, f"{prefix}_{new}")
        if dup is not None:
            _LOGGER.info("selpi: removing %s (duplicate of %s after the %s -> %s rename)", dup, old_id, old, new)
            reg.async_remove(dup)
        reg.async_update_entity(old_id, new_unique_id=f"{prefix}_{new}")


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


def _repair_nondefault_enabled(hass: HomeAssistant, entry: SelpiConfigEntry, fields: list) -> None:
    """One-time fix for the 0.6.0 bug where _apply_esp_present re-enabled every INTEGRATION-disabled entity when
    the ESP was absent — including the infrequently-used (non-default) field sensors that are meant to stay
    disabled. Re-disable those once; the guard flag means a sensor the user enables afterwards stays enabled."""
    if entry.data.get(NONDEFAULT_REPAIRED):
        return
    reg = er.async_get(hass)
    prefix = entry.unique_id or entry.entry_id
    for f in fields:
        if f.get("default"):
            continue
        eid = reg.async_get_entity_id("sensor", DOMAIN, f"{prefix}_{f['key']}")
        if eid is None:
            continue
        ent = reg.async_get(eid)
        if ent and ent.disabled_by is None:
            reg.async_update_entity(eid, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
    hass.config_entries.async_update_entry(entry, data={**entry.data, NONDEFAULT_REPAIRED: True})


async def _options_updated(hass: HomeAssistant, entry: SelpiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SelpiConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
