"""selpi integration against a mocked add-on API."""
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.selpi.const import CONF_ADDON_SLUG, CONF_SCAN_INTERVAL, CONF_TOKEN, DOMAIN

BASE = "http://local-selpi:8100/api/v1"
INFO = {"id": "unit123", "connection": "SelectLive", "scan_interval": 60, "model": "SP PRO",
        "manufacturer": "Selectronic", "firmware": "15.47", "versions": {"memory_map": 31}, "version_problems": [],
        "buttons": ["generator", "silence", "on"]}
FIELDS = [
    {"key": "load_ac_power", "name": "Load power", "unit": "kW", "kind": "number", "default": True,
     "device_class": "power", "state_class": "measurement", "precision": 3, "category": None, "note": ""},
    {"key": "ac_out_status", "name": "Inverter mode", "unit": "", "kind": "enum", "default": True,
     "device_class": "enum", "state_class": None, "precision": None, "category": None, "note": "",
     "options": ["Econo", "Idle", "On", "Sync"]},
    {"key": "ac_loadk_wh_acc", "name": "Load energy today", "unit": "kWh", "kind": "number", "default": True,
     "device_class": "energy", "state_class": "total_increasing", "precision": 2, "category": None, "note": ""},
    {"key": "country_code", "name": "Country Code", "unit": "", "kind": "raw", "default": False,
     "device_class": None, "state_class": "measurement", "precision": 0, "category": "diagnostic", "note": ""},
]
VALUES = {"at": "2026-11-17T18:00:00", "stale": False, "version_problems": [],
          "values": {"load_ac_power": 2.026, "ac_out_status": "Sync", "ac_loadk_wh_acc": 17.88, "country_code": 36}}
DIAG = {"last_ok": "2026-11-17T18:00:00+08:00", "last_error": None, "busy": None,
        "clock": {"drift": 3}, "backup_running": False,
        "last_backup": {"name": "2026-11-17_03-30-00", "reason": "scheduled", "at": "2026-11-17T03:30:00+08:00"}}
DATA = {CONF_HOST: "local-selpi", CONF_PORT: 8100, CONF_TOKEN: "tok", CONF_ADDON_SLUG: "local_selpi"}


def mock_api(aioclient_mock, values=VALUES, info=INFO, fields=FIELDS):
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/info", json=info)
    aioclient_mock.get(f"{BASE}/fields", json={"fields": fields})
    aioclient_mock.get(f"{BASE}/values", json=values)
    aioclient_mock.get(f"{BASE}/diagnostics", json=DIAG)
    aioclient_mock.post(f"{BASE}/backup", json={"started": True})
    aioclient_mock.post(f"{BASE}/button", json={"pressed": "generator", "register": "0xa232", "read_back": [0, 0]})


async def setup(hass, aioclient_mock, **kw):
    mock_api(aioclient_mock, **kw)
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="unit123")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_sensors_and_device(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock)
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert hass.states.get("sensor.sp_pro_load_power").state == "2.026"
    st = hass.states.get("sensor.sp_pro_inverter_mode")
    assert st.state == "Sync" and st.attributes["options"] == ["Econo", "Idle", "On", "Sync"]
    energy = hass.states.get("sensor.sp_pro_load_energy_today")
    assert energy.attributes["state_class"] == "total_increasing" and energy.attributes["unit_of_measurement"] == "kWh"
    assert hass.states.get("sensor.sp_pro_clock_drift").state == "3"
    assert hass.states.get("sensor.sp_pro_last_config_backup").state == "2026-11-16T19:30:00+00:00"
    assert hass.states.get("sensor.sp_pro_link_status").state == "OK"
    # non-default fields exist but are disabled, and aren't polled
    reg = er.async_get(hass).async_get("sensor.sp_pro_country_code")
    assert reg.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    polled = [str(url.query.get("keys")) for method, url, *_ in aioclient_mock.mock_calls if url.path.endswith("/values")]
    assert polled and "country_code" not in polled[-1] and "load_ac_power" in polled[-1]
    dev = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, "unit123"), entry.entry_id)
    assert dev.sw_version == "15.47" and dev.manufacturer == "Selectronic"
    assert dev.configuration_url == "homeassistant://hassio/ingress/local_selpi"


async def test_scan_interval_from_addon_and_options(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock)
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == 60
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SCAN_INTERVAL: 15})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == 15


async def test_local_connection_default_is_faster(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock, info={**INFO, "connection": "TCP", "scan_interval": 10})
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == 10


async def test_version_gate(hass: HomeAssistant, aioclient_mock):
    bad = {**VALUES, "version_problems": ["memory_map 32 (verified 31)"]}
    entry = await setup(hass, aioclient_mock, values=bad)
    assert entry.state is config_entries.ConfigEntryState.SETUP_RETRY


async def test_stale_values_still_shown(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock)
    mock_api(aioclient_mock, values={**VALUES, "stale": True})
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.sp_pro_load_power").attributes.get("stale") is True
    assert hass.states.get("sensor.sp_pro_link_status").state.startswith("busy")


async def test_unknown_enum_code(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock)
    mock_api(aioclient_mock, values={**VALUES, "values": {**VALUES["values"], "ac_out_status": "code 9"}})
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.sp_pro_inverter_mode").state == "code 9"


async def test_addon_down_makes_entities_unavailable(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/values", status=502, json={"error": "select.live timeout"})
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.sp_pro_load_power").state == "unavailable"
    assert "select.live timeout" in hass.states.get("sensor.sp_pro_link_status").state


async def test_backup_button(hass: HomeAssistant, aioclient_mock):
    await setup(hass, aioclient_mock)
    await hass.services.async_call("button", "press", {"entity_id": "button.sp_pro_back_up_settings"}, blocking=True)
    assert any(m == "POST" and u.path.endswith("/backup") for m, u, *_ in aioclient_mock.mock_calls)


async def test_flow_hassio_discovery(hass: HomeAssistant, aioclient_mock):
    mock_api(aioclient_mock)
    info = HassioServiceInfo(config={"host": "local-selpi", "port": 8100, "token": "tok"},
                             name="selpi", slug="local_selpi", uuid="x")
    with patch("custom_components.selpi.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO},
                                                           data=info)
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "hassio_confirm"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == DATA and result["result"].unique_id == "unit123"


async def test_flow_manual_bad_token(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(f"{BASE}/info", status=401, json={"error": "bad or missing token"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "local-selpi", CONF_PORT: 8100, CONF_TOKEN: "wrong"})
    assert result["errors"] == {"base": "invalid_auth"}
    mock_api(aioclient_mock)
    with patch("custom_components.selpi.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "local-selpi", CONF_PORT: 8100, CONF_TOKEN: "tok"})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_discovery_of_configured_unit_updates_entry(hass: HomeAssistant, aioclient_mock):
    entry = MockConfigEntry(domain=DOMAIN, data={**DATA, CONF_TOKEN: "old"}, unique_id="unit123")
    entry.add_to_hass(hass)
    mock_api(aioclient_mock)
    info = HassioServiceInfo(config={"host": "local-selpi", "port": 8100, "token": "tok"},
                             name="selpi", slug="local_selpi", uuid="x")
    with patch("custom_components.selpi.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO},
                                                           data=info)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    assert entry.data[CONF_TOKEN] == "tok"


async def test_front_panel_buttons(hass: HomeAssistant, aioclient_mock):
    await setup(hass, aioclient_mock)
    assert hass.states.get("button.sp_pro_silence_alarm") is not None
    await hass.services.async_call("button", "press", {"entity_id": "button.sp_pro_generator_start_stop"}, blocking=True)
    calls = [(m, u) for m, u, *_ in aioclient_mock.mock_calls if m == "POST" and u.path.endswith("/button")]
    assert len(calls) == 1 and calls[0][1].query.get("name") == "generator"


async def test_no_panel_buttons_from_an_older_app(hass: HomeAssistant, aioclient_mock):
    await setup(hass, aioclient_mock, info={k: v for k, v in INFO.items() if k != "buttons"})
    assert hass.states.get("button.sp_pro_generator_start_stop") is None
    assert hass.states.get("button.sp_pro_back_up_settings") is not None


async def test_on_button_disabled_and_needs_a_second_press(hass: HomeAssistant, aioclient_mock):
    from homeassistant.exceptions import HomeAssistantError
    entry = await setup(hass, aioclient_mock)
    reg = er.async_get(hass)
    ent = reg.async_get("button.sp_pro_inverter_on_idle_long_press")
    assert ent.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    reg.async_update_entity(ent.entity_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    on_calls = lambda: [u for m, u, *_ in aioclient_mock.mock_calls
                        if m == "POST" and u.path.endswith("/button") and u.query.get("name") == "on"]
    with pytest.raises(HomeAssistantError, match="Press again"):
        await hass.services.async_call("button", "press", {"entity_id": ent.entity_id}, blocking=True)
    assert on_calls() == []
    await hass.services.async_call("button", "press", {"entity_id": ent.entity_id}, blocking=True)
    assert len(on_calls()) == 1 and on_calls()[0].query.get("confirm") == "outage"


CTRL_INFO = {**INFO, "controls": ["equalise", "generator", "output"]}
CTRL_VALUES = {**VALUES, "values": {**VALUES["values"], "generator_status_from_led": "Not Running"}}


def control_calls(aioclient_mock, name=None):
    return [u for m, u, *_ in aioclient_mock.mock_calls
            if m == "POST" and u.path.endswith("/control") and (name is None or u.query.get("name") == name)]


async def test_controls_replace_toggling_buttons(hass: HomeAssistant, aioclient_mock):
    await setup(hass, aioclient_mock, info=CTRL_INFO, values=CTRL_VALUES)
    assert hass.states.get("button.sp_pro_generator_start_stop") is None
    assert er.async_get(hass).async_get("button.sp_pro_inverter_on_idle_long_press") is None
    assert hass.states.get("button.sp_pro_silence_alarm") is not None
    assert hass.states.get("button.sp_pro_request_equalise") is not None
    assert hass.states.get("switch.sp_pro_generator").state == "off"


async def test_generator_switch_tracks_the_unit(hass: HomeAssistant, aioclient_mock):
    entry = await setup(hass, aioclient_mock, info=CTRL_INFO, values=CTRL_VALUES)
    aioclient_mock.post(f"{BASE}/control", json={"control": "generator", "state": "on", "pressed": True})
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.sp_pro_generator"}, blocking=True)
    calls = control_calls(aioclient_mock, "generator")
    assert len(calls) == 1 and calls[0].query.get("state") == "on"
    # the unit reports Starting (whoever started it): the switch follows
    for label, state in (("Starting", "on"), ("Running", "on"), ("Stopping", "off"), ("AC Source Present", "off")):
        mock_api(aioclient_mock, info=CTRL_INFO,
                 values={**VALUES, "values": {**VALUES["values"], "generator_status_from_led": label}})
        await entry.runtime_data.coordinator.async_refresh()
        await hass.async_block_till_done()
        s = hass.states.get("switch.sp_pro_generator")
        assert (s.state, s.attributes["sp_pro_state"]) == (state, label)


async def test_generator_refusal_is_an_error(hass: HomeAssistant, aioclient_mock):
    from homeassistant.exceptions import HomeAssistantError
    await setup(hass, aioclient_mock, info=CTRL_INFO, values=CTRL_VALUES)
    aioclient_mock.post(f"{BASE}/control", status=409,
                        json={"error": "generator is AC Source Present: the SP PRO will not start it from the button"})
    with pytest.raises(HomeAssistantError, match="AC Source Present"):
        await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.sp_pro_generator"}, blocking=True)


async def test_output_switch_disabled_and_idle_needs_a_second_turn_off(hass: HomeAssistant, aioclient_mock):
    from homeassistant.exceptions import HomeAssistantError
    entry = await setup(hass, aioclient_mock, info=CTRL_INFO, values=CTRL_VALUES)
    reg = er.async_get(hass)
    ent = reg.async_get("switch.sp_pro_inverter_output")
    assert ent.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    reg.async_update_entity(ent.entity_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ent.entity_id).state == "on"          # Sync
    aioclient_mock.post(f"{BASE}/control", json={"control": "output", "state": "idle", "pressed": True})
    with pytest.raises(HomeAssistantError, match="again within"):
        await hass.services.async_call("switch", "turn_off", {"entity_id": ent.entity_id}, blocking=True)
    assert control_calls(aioclient_mock, "output") == []
    await hass.services.async_call("switch", "turn_off", {"entity_id": ent.entity_id}, blocking=True)
    calls = control_calls(aioclient_mock, "output")
    assert len(calls) == 1 and calls[0].query.get("state") == "idle" and calls[0].query.get("confirm") == "outage"
    await hass.services.async_call("switch", "turn_on", {"entity_id": ent.entity_id}, blocking=True)
    assert control_calls(aioclient_mock, "output")[-1].query.get("state") == "on"


async def test_equalise_button(hass: HomeAssistant, aioclient_mock):
    await setup(hass, aioclient_mock, info=CTRL_INFO, values=CTRL_VALUES)
    aioclient_mock.post(f"{BASE}/control", json={"control": "equalise", "state": "", "pressed": True})
    await hass.services.async_call("button", "press", {"entity_id": "button.sp_pro_request_equalise"}, blocking=True)
    calls = control_calls(aioclient_mock, "equalise")
    assert len(calls) == 1 and "state" not in calls[0].query


async def test_renamed_key_keeps_its_entity(hass: HomeAssistant, aioclient_mock):
    reg = er.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="unit123")
    entry.add_to_hass(hass)
    old = reg.async_get_or_create("sensor", DOMAIN, "unit123_daysto_recharge", config_entry=entry,
                                  suggested_object_id="sp_pro_days_to_recharge")
    fields = FIELDS + [{"key": "days_to_recharge", "name": "Days to Recharge", "unit": "", "kind": "number",
                        "default": False, "device_class": None, "state_class": "measurement", "precision": 0,
                        "category": None, "note": ""}]
    mock_api(aioclient_mock, fields=fields)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert reg.async_get(old.entity_id).unique_id == "unit123_days_to_recharge"


async def test_renamed_key_with_a_duplicate_from_an_older_integration(hass: HomeAssistant, aioclient_mock):
    """App updated first: the old integration already made sensor..._2 for the new key."""
    reg = er.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="unit123")
    entry.add_to_hass(hass)
    old = reg.async_get_or_create("sensor", DOMAIN, "unit123_daysto_equalise", config_entry=entry,
                                  suggested_object_id="sp_pro_days_to_equalise")
    dup = reg.async_get_or_create("sensor", DOMAIN, "unit123_days_to_equalise", config_entry=entry,
                                  suggested_object_id="sp_pro_days_to_equalise_2")
    fields = FIELDS + [{"key": "days_to_equalise", "name": "Days to equalise", "unit": "", "kind": "number",
                        "default": True, "device_class": None, "state_class": "measurement", "precision": 0,
                        "category": None, "note": ""}]
    mock_api(aioclient_mock, fields=fields)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert reg.async_get(old.entity_id).unique_id == "unit123_days_to_equalise"
    assert reg.async_get(dup.entity_id) is None
