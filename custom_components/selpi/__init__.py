"""Selectronic SP PRO via the selpi add-on.

The add-on owns the link to the inverter (Select.Live, serial, or TCP through the ESP proxy); this
integration only asks the add-on's API for values and turns them into a device with sensors.
"""
from __future__ import annotations

import logging

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SelpiAuthError, SelpiClient, SelpiError
from .const import CONF_TOKEN, DOMAIN
from .coordinator import SelpiConfigEntry, SelpiCoordinator, SelpiRuntime

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]
# field keys renamed in selpi 0.4.7 (SP LINK's "DaystoEqualise" split badly): keep the entities
RENAMED_KEYS = {"daysto_recharge": "days_to_recharge", "daysto_equalise": "days_to_equalise"}


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


async def _options_updated(hass: HomeAssistant, entry: SelpiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SelpiConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
