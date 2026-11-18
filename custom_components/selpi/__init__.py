"""Selectronic SP PRO via the selpi add-on.

The add-on owns the link to the inverter (Select.Live, serial, or TCP through the ESP proxy); this
integration only asks the add-on's API for values and turns them into a device with sensors.
"""
from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SelpiAuthError, SelpiClient, SelpiError
from .const import CONF_TOKEN
from .coordinator import SelpiConfigEntry, SelpiCoordinator, SelpiRuntime

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


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
    coordinator = SelpiCoordinator(hass, entry, client, info, [f["key"] for f in fields if f.get("default")])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = SelpiRuntime(client=client, info=info, fields=fields, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass: HomeAssistant, entry: SelpiConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SelpiConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
