"""Set up from the add-on's Supervisor discovery, or by hand (host, port, token)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .api import SelpiAuthError, SelpiClient, SelpiError
from .const import (
    CONF_ADDON_SLUG,
    CONF_ESP_PRESENT,
    CONF_FAST_SCAN_INTERVAL,
    CONF_GRACE,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_GRACE_SECONDS,
    DEFAULT_PORT,
    DOMAIN,
    MAX_FAST_SCAN_INTERVAL,
    MAX_GRACE,
    MAX_SCAN_INTERVAL,
    MIN_FAST_SCAN_INTERVAL,
    MIN_GRACE,
    MIN_SCAN_INTERVAL,
)
from .esp import esp_active


class SelpiConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}

    async def _probe(self, data: dict[str, Any]) -> dict[str, Any]:
        client = SelpiClient(async_get_clientsession(self.hass), data[CONF_HOST], data[CONF_PORT],
                             data[CONF_TOKEN])
        return await client.info()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await self._probe(user_input)
            except SelpiAuthError:
                errors["base"] = "invalid_auth"
            except SelpiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["id"])
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(title="SP PRO", data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "local-selpi")): str,
            vol.Required(CONF_PORT, default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_TOKEN): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        cfg = discovery_info.config
        data = {CONF_HOST: cfg["host"], CONF_PORT: int(cfg["port"]), CONF_TOKEN: cfg["token"],
                CONF_ADDON_SLUG: discovery_info.slug}
        try:
            info = await self._probe(data)
        except SelpiError:
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(info["id"])
        # the add-on may have moved (new hostname/token after a reinstall): keep the entry current
        self._abort_if_unique_id_configured(updates=data)
        self._discovered = data
        self.context["title_placeholders"] = {"name": discovery_info.name or "selpi"}
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="SP PRO", data=self._discovered)
        return self.async_show_form(step_id="hassio_confirm",
                                    description_placeholders={"addon": self.context["title_placeholders"]["name"]})

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, CONF_TOKEN: user_input[CONF_TOKEN]}
            try:
                await self._probe(data)
            except SelpiAuthError:
                errors["base"] = "invalid_auth"
            except SelpiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
                                    errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SelpiOptionsFlow()


class SelpiOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        entry = self.config_entry
        runtime = getattr(entry, "runtime_data", None)
        suggested = runtime.info.get("scan_interval") if runtime else 60
        current = entry.options.get(CONF_SCAN_INTERVAL) or suggested or 60
        fast_current = entry.options.get(CONF_FAST_SCAN_INTERVAL) or DEFAULT_FAST_SCAN_INTERVAL
        # how long to keep the last values on a failed poll before entities go unavailable: default to the
        # add-on's own stale-grace (0 on a direct/local link = fast 'unknown', longer on Select.Live).
        grace_current = entry.options.get(CONF_GRACE)
        if grace_current is None:
            grace_current = runtime.info.get("stale_grace") if runtime else None
        if grace_current is None:
            grace_current = DEFAULT_GRACE_SECONDS
        esp_default = esp_active(entry, runtime.info if runtime else {})   # user's choice, else connection type
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current):
                vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            vol.Required(CONF_FAST_SCAN_INTERVAL, default=fast_current):
                vol.All(vol.Coerce(int), vol.Range(min=MIN_FAST_SCAN_INTERVAL, max=MAX_FAST_SCAN_INTERVAL)),
            vol.Required(CONF_GRACE, default=grace_current):
                vol.All(vol.Coerce(int), vol.Range(min=MIN_GRACE, max=MAX_GRACE)),
            vol.Required(CONF_ESP_PRESENT, default=esp_default): bool,
        })
        return self.async_show_form(step_id="init", data_schema=schema,
                                    description_placeholders={"suggested": str(suggested)})
