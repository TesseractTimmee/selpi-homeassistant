"""
ESPHome external component: Selectronic SP PRO over its native link (USB CDC, or any UART stream).

Reads the same memory blocks SP LINK's data screens read and publishes chosen fields as sensors /
text sensors. The field table (live_fields.json, splink_tables.json) is selpi's, matching
SP LINK 15.40 for memory map 31; keep the copies here in sync
with selpi/sppro/ (tools/sync_fields.sh in this repo).

Optional buttons: the SP PRO's front panel buttons as ESPHome buttons (generator start/stop and silence
alarm: short press; on_idle: the ON button's long press, ON <-> IDLE, disabled by default and needing a second press within 30 s),
pressed the way SP LINK's Quick View front panel does (see selpi docs/protocol.md). Also `identify`: flash the
SP PRO's front panel LEDs to locate it (SP LINK's btnIdentify; a benign momentary write to 0xa389, no passcode).

Optional controls (state-aware, selpi sppro/controls.py): `generator` and `output` switches whose state is the
unit's own (Generator Status / Output Mode, whatever started or stopped it); switching reads the state fresh and
presses Generator (short) / ON (long) only if that changes something. Output off = IDLE (no AC output): disabled
by default, needs a second request within 30 s. `equalise`: a button for the equalise request (two long
Generator presses).

Optional proxy: a TCP port that passes raw SP PRO frames (selpi, SP LINK) through, interleaved with
the component's own polling. Clients in `allowed_ips` are read-only (login frames pass); clients in `write_ips`
may also write (e.g. SP LINK).
"""
import json
import os
import re

import esphome.codegen as cg
from esphome.components import button, sensor, socket, switch, text_sensor, time as time_, uart
import esphome.config_validation as cv

from . import field_meta
from esphome.const import (
    CONF_ID,
    CONF_KEY,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_STATUS,
    CONF_TIMEOUT,
    ENTITY_CATEGORY_CONFIG,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL,
    STATE_CLASS_TOTAL_INCREASING,
)

CODEOWNERS = []
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["button", "sensor", "switch", "text_sensor", "md5", "socket"]

CONF_FIELDS = "fields"
CONF_ALL_FIELDS = "all_fields"
CONF_FEATURES = "features"          # feature groups this unit has; the default field set drops fields needing others
CONF_MAP_VERSION = "map_version"    # this unit's memory-map version; drops default fields that need a newer one
FEATURES = ("ac_solar", "bms", "battery")   # mirrors sppro.live FEATURE_PROBE + batteryless
CONF_PROXY = "proxy"
CONF_ALLOWED_IPS = "allowed_ips"
CONF_WRITE_IPS = "write_ips"
CONF_LOG_DOWNLOADS = "log_downloads"
CONF_ERRORS = "errors"
CONF_VERSIONS = "versions"
CONF_ALLOW_VERSION_MISMATCH = "allow_version_mismatch"
CONF_CLOCK = "clock"
CONF_TIME_ID = "time_id"
CONF_INTERVAL = "interval"
CONF_MAX_DRIFT = "max_drift"
CONF_SET = "set"
CONF_DRIFT = "drift"
CONF_BUTTONS = "buttons"
CONF_CONTROLS = "controls"
CONF_UNITS = "units"            # Powerchain: one block per physical inverter (phase + role + its fields)
CONF_SYSTEM = "system"          # the whole-site aggregated device (sum power/energy, avg SoC/volts)
CONF_PHASE = "phase"
CONF_ROLE = "role"
CONF_SERIAL = "serial"
PHASES = {"L1": 1, "L2": 2, "L3": 3, "Split": 4}      # the 0xc0ee phase codes (manager = phase, worker = phase+4)
ROLES = {"manager": 0, "worker": 1}
CONTROLS = {"generator": 0, "output": 1}
# fields whose words the controls need polled (their switch state), plus what shows an equalise request
CONTROL_KEYS = ["generator_status_from_led", "ac_out_status", "days_to_equalise"]
BUTTONS = {"generator": 0, "on_idle": 1, "silence": 2, "identify": 4}   # "on" would be read as YAML true

_HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = json.load(open(os.path.join(_HERE, "live_fields.json"), encoding="utf-8"))
ENUMS = json.load(open(os.path.join(_HERE, "splink_tables.json"), encoding="utf-8"))
FIELDS = {f["key"]: f for f in TABLE["fields"]}
# keys renamed in 0.4.7 (SP LINK's "DaystoEqualise" split badly): the old ones still work
KEY_ALIASES = {"daysto_recharge": "days_to_recharge", "daysto_equalise": "days_to_equalise"}
SCALES = ["AcVolts", "AcCurrent", "DcVolts", "DcCurrent", "Temperature", "InternalVoltages"]
SCALE_BASE = 0xA028
VERSION_BASE, VERSION_WORDS = 0xA007, 25
# config settings, service settings, memory map, event/detailed/daily log formats (0xa007..0xa00c).
# The field table was built and checked at these; see selpi docs/protocol.md "Version block".
VERIFIED_VERSIONS = [48, 14, 31, 3, 3, 5]

# A sensible default set (HA names), shared with the selpi add-on's HA API (sppro/default_fields.json).
# Any key from live_fields.json can be added under `fields:`.
DEFAULT_FIELDS = json.load(open(os.path.join(_HERE, "default_fields.json"), encoding="utf-8"))


def _field_available(f, features, map_version):
    """Whether a field applies to this unit (mirrors sppro.live.field_available). None = unspecified -> keep.
    Used only for the default field set; fields listed explicitly in YAML are always honoured."""
    feat = f.get("feature")
    if feat and features is not None and feat not in features:
        return False
    need = f.get("needs_map_version")
    if need and map_version is not None and map_version < need:
        return False
    return True

# state_class string (from field_meta.hints) -> ESPHome constant
_STATE_CLASS = {"measurement": STATE_CLASS_MEASUREMENT, "total": STATE_CLASS_TOTAL,
                "total_increasing": STATE_CLASS_TOTAL_INCREASING}

sppro_ns = cg.esphome_ns.namespace("sppro")
SpPro = sppro_ns.class_("SpPro", cg.PollingComponent, uart.UARTDevice)
SpProButton = sppro_ns.class_("SpProButton", button.Button, cg.Parented.template(SpPro))
SpProSwitch = sppro_ns.class_("SpProSwitch", switch.Switch, cg.Parented.template(SpPro))
Agg = sppro_ns.enum("Agg", is_class=True)   # how a field rolls up to the System device

# System totals: powers/energies/currents add, voltages/SoC/frequency average, everything else has no
# whole-system value. Must match the add-on's sppro/multiphase.py (SUM_UNITS/AVG_UNITS/PER_UNIT_ONLY) so the
# ESP and the app agree; keep PER_UNIT_ONLY in sync with that module.
_SUM_UNITS = {"kWh", "Wh", "kW", "W", "A", "Ah", "kvar", "var", "kVA", "VA"}
_AVG_UNITS = {"V", "%", "Hz", "°C", "C"}
_PER_UNIT_ONLY = {
    "battery_temperature", "control_board_temperature", "heatsink_temperature",
    "inlet_air_temperature", "transformer_temperature",
    "fan_speed", "fan_life", "capacitor_life_consumed_filter",
    "capacitor_life_consumed_pm1", "capacitor_life_consumed_pm2",
    "general_purpose1", "general_purpose2", "load_volts_high_frequency_ripple", "battery_mid_point",
    "multi_phase_ac_source_volts_l1", "multi_phase_load_ac_volts_l1",
    "dc_shunt1_peak_power_previous", "dc_shunt2_peak_power_previous",
    "shunt1_peak_power_today", "shunt2_peak_power_today",
    "sys_reg_charge_power_limit", "sys_reg_export_power_limit",
    "fan_life_in_service_tab", "batt_soc_percent_in_service_tab",
    "i_shunt1_in_service_tab", "i_shunt2_in_service_tab",
}


def _aggregation(unit, key=None):
    if key in _PER_UNIT_ONLY:
        return None
    if unit in _SUM_UNITS:
        return "sum"
    if unit in _AVG_UNITS:
        return "avg"
    return None


SCREEN_NAMES = {
    "NowSubTab": "now", "TodaySubTab": "today", "TechnicalDataSubTab": "tech", "DCHistorySubTab": "DC history",
    "ACHistorySubTab": "AC history", "ACHistorySubTab2": "AC history 2", "ServiceReadings1": "service",
    "ServiceSettings": "service settings", "Now_Today_Tech_KacoModelsCapacityAndOEM": "unit",
}


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _field_entry(value):
    if isinstance(value, str):
        value = {CONF_KEY: value}
    value = cv.Schema({cv.Required(CONF_KEY): cv.string}, extra=cv.ALLOW_EXTRA)(value)
    value[CONF_KEY] = KEY_ALIASES.get(value[CONF_KEY], value[CONF_KEY])
    if value[CONF_KEY] not in FIELDS:
        raise cv.Invalid("unknown SP PRO field '%s' (see live_fields.json, or `selpi live --list`)" % value[CONF_KEY])
    return value


def _entity_schema(f):
    if f["kind"] == "enum":
        return text_sensor.text_sensor_schema()
    h = field_meta.hints(f)      # shared with the selpi app / HA integration
    kw = dict(accuracy_decimals=h["precision"] if h["precision"] is not None else 2)
    if h["state_class"]:
        kw["state_class"] = _STATE_CLASS[h["state_class"]]
    if h["device_class"]:
        kw["device_class"] = h["device_class"]
    if h["category"] == "diagnostic":
        kw["entity_category"] = ENTITY_CATEGORY_DIAGNOSTIC
    if f["unit"]:
        kw["unit_of_measurement"] = f["unit"]
    return sensor.sensor_schema(**kw)


def _expand_entities(entries, prefix=""):
    """Validate a field list into entity configs, names prefixed with `prefix` (e.g. "L1 Manager"). A non-default
    field (not in the default set) comes disabled_by_default, like the HA integration - declared but off until
    enabled in HA (no reflash)."""
    out, names = [], set()
    for e in entries:
        f = FIELDS[e[CONF_KEY]]
        conf = {k: v for k, v in e.items() if k not in (CONF_KEY, CONF_PHASE, CONF_ROLE, CONF_SERIAL)}
        if CONF_NAME not in conf:
            name = field_meta.field_name(f["key"], f["name"], DEFAULT_FIELDS.get(f["key"]))
            if _slug(name) in names:   # same label on two screens: say which
                name = "%s (%s)" % (name, SCREEN_NAMES.get(f["screen"], f["screen"]))
            if _slug(name) in names:
                name = "%s (%s)" % (name, f["key"])
            names.add(_slug(name))
            conf[CONF_NAME] = ("%s %s" % (prefix, name)) if prefix else name
        else:
            names.add(_slug(conf[CONF_NAME]))
        if "disabled_by_default" not in conf and e[CONF_KEY] not in DEFAULT_FIELDS:
            conf["disabled_by_default"] = True
        conf = _entity_schema(f)(conf)
        conf[CONF_KEY] = f["key"]
        out.append(conf)
    return out


def _build(config):
    """Assemble the internal unit list (single inverter = one L1 manager) + the System field set, and name
    adaptively: the phase is dropped when the whole site is one phase, the role when a phase has no worker."""
    raw = config.get(CONF_UNITS)
    if raw is None:
        raw = [{CONF_PHASE: "L1", CONF_ROLE: "manager", CONF_FIELDS: config.get(CONF_FIELDS)}]
    elif CONF_FIELDS in config:
        raise cv.Invalid("use either `fields:` (single inverter) or `units:` (Powerchain), not both")

    by_phase_role = {}
    for u in raw:
        by_phase_role.setdefault((u[CONF_PHASE], u[CONF_ROLE]), []).append(u)
    for (phase, role), us in by_phase_role.items():
        if role == "manager" and len(us) > 1:
            raise cv.Invalid("phase %s has %d managers; only one is allowed" % (phase, len(us)))
        if role == "worker" and len(us) >= 2 and any(CONF_SERIAL not in w for w in us):
            raise cv.Invalid("phase %s has %d workers; give each a `serial:` so they can be told apart "
                             "(from `selpi live` / the add-on's /api/v1/units)" % (phase, len(us)))

    feats = config.get(CONF_FEATURES)          # None = keep all; a list gates the default field set
    mapv = config.get(CONF_MAP_VERSION)
    default_entries = [{CONF_KEY: k} for k in DEFAULT_FIELDS if _field_available(FIELDS[k], feats, mapv)]

    phases = {u[CONF_PHASE] for u in raw}
    multi_phase = len(phases) > 1
    phase_has_worker = {p: any(u[CONF_PHASE] == p and u[CONF_ROLE] == "worker" for u in raw) for p in phases}
    units = []
    for u in raw:
        prefix = u[CONF_PHASE] if multi_phase else ""
        if phase_has_worker[u[CONF_PHASE]]:
            prefix = ("%s %s" % (prefix, u[CONF_ROLE].capitalize())).strip()
        entries = u.get(CONF_FIELDS) or default_entries
        units.append({CONF_PHASE: u[CONF_PHASE], CONF_ROLE: u[CONF_ROLE], CONF_SERIAL: u.get(CONF_SERIAL, 0),
                      "_entities": _expand_entities(entries, prefix)})

    config = dict(config)
    config["_units"] = units
    config["_multi"] = len(units) > 1
    config["_system"] = []
    sysc = config.get(CONF_SYSTEM, config["_multi"])    # default: on when multi, off when single
    if config["_multi"] and sysc not in (False, None):
        entries = (sysc.get(CONF_FIELDS) if isinstance(sysc, dict) and sysc.get(CONF_FIELDS) else
                   default_entries)
        entries = [e for e in entries if _aggregation(FIELDS[e[CONF_KEY]]["unit"], e[CONF_KEY])]   # only roll-up-able fields
        config["_system"] = _expand_entities(entries, "")
    return config


PROXY_SCHEMA = cv.Schema({
    cv.Required(CONF_PORT): cv.port,
    cv.Optional(CONF_ALLOWED_IPS): socket.IPV4_ALLOW_SCHEMA,   # may connect (read-only)
    cv.Optional(CONF_WRITE_IPS, default=[]): socket.IPV4_ALLOW_SCHEMA,  # may connect and write
    # read-only clients may still make the writes a log download needs (0xa251, log search ranges)
    cv.Optional(CONF_LOG_DOWNLOADS, default=True): cv.boolean,
})


CLOCK_SCHEMA = cv.Schema({
    cv.Required(CONF_TIME_ID): cv.use_id(time_.RealTimeClock),   # e.g. sntp_time
    cv.Optional(CONF_INTERVAL, default="1h"): cv.positive_time_period_milliseconds,
    cv.Optional(CONF_MAX_DRIFT, default="10s"): cv.positive_time_period_seconds,
    cv.Optional(CONF_SET, default=True): cv.boolean,   # false: only report the drift
    cv.Optional(CONF_DRIFT): sensor.sensor_schema(unit_of_measurement="s", accuracy_decimals=0,
                                                  device_class="duration", state_class=STATE_CLASS_MEASUREMENT,
                                                  entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
})


BUTTONS_SCHEMA = cv.Schema({
    cv.Optional("generator"): button.button_schema(SpProButton, icon="mdi:engine"),
    cv.Optional("silence"): button.button_schema(SpProButton, icon="mdi:volume-off"),
    # identify: flash the SP PRO's front panel LEDs to locate it (benign momentary write, no passcode)
    cv.Optional("identify"): button.button_schema(SpProButton, icon="mdi:led-on"),
    # ON <-> IDLE cuts the AC output: off in HA until enabled, and two presses within 30 s
    cv.Optional("on_idle"): button.button_schema(SpProButton, icon="mdi:power", entity_category=ENTITY_CATEGORY_CONFIG)
    .extend({cv.Optional("disabled_by_default", default=True): cv.boolean}),
})


def _no_restore(config):
    # a restored / boot state would press a button at startup: these switches only follow the unit
    if str(config.get("restore_mode", "DISABLED")).upper() != "DISABLED":
        raise cv.Invalid("SP PRO control switches follow the unit's state: restore_mode must be DISABLED")
    return config


CONTROLS_SCHEMA = cv.Schema({
    cv.Optional("generator"): cv.All(switch.switch_schema(SpProSwitch, icon="mdi:engine",
                                                          default_restore_mode="DISABLED"), _no_restore),
    # IDLE cuts the AC output: off in HA until enabled, and turning off takes two requests within 30 s
    cv.Optional("output"): cv.All(switch.switch_schema(SpProSwitch, icon="mdi:power",
                                                       entity_category=ENTITY_CATEGORY_CONFIG,
                                                       default_restore_mode="DISABLED")
                                  .extend({cv.Optional("disabled_by_default", default=True): cv.boolean}),
                                  _no_restore),
    cv.Optional("equalise"): button.button_schema(SpProButton, icon="mdi:battery-sync"),
})


UNIT_SCHEMA = cv.Schema({
    cv.Optional(CONF_PHASE, default="L1"): cv.one_of(*PHASES, space=""),
    cv.Optional(CONF_ROLE, default="manager"): cv.one_of(*ROLES, lower=True),
    cv.Optional(CONF_SERIAL): cv.positive_int,      # pin a specific inverter (needed for 2+ workers on a phase)
    cv.Optional(CONF_FIELDS): cv.ensure_list(_field_entry),
})
# system: true/false, or a dict with its own `fields:` (only aggregatable fields are kept)
SYSTEM_SCHEMA = cv.Any(cv.boolean, cv.Schema({cv.Optional(CONF_FIELDS): cv.ensure_list(_field_entry)}))


def _proxy_sockets(config):
    if CONF_PROXY in config:
        socket.consume_sockets(1, "sppro", socket.SocketType.TCP_LISTEN)(config)
        socket.consume_sockets(1, "sppro")(config)
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema({
        cv.GenerateID(): cv.declare_id(SpPro),
        cv.Required(CONF_PASSWORD): cv.string,
        cv.Optional(CONF_TIMEOUT, default="1500ms"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_FIELDS): cv.ensure_list(_field_entry),          # single inverter (shorthand for one unit)
        cv.Optional(CONF_UNITS): cv.ensure_list(UNIT_SCHEMA),            # Powerchain: one block per inverter
        cv.Optional(CONF_SYSTEM): SYSTEM_SCHEMA,                          # whole-site totals device
        cv.Optional(CONF_ALLOW_VERSION_MISMATCH, default=False): cv.boolean,
        cv.Optional(CONF_FEATURES): cv.ensure_list(cv.one_of(*FEATURES, lower=True)),   # gate the default field set
        cv.Optional(CONF_MAP_VERSION): cv.positive_int,
        cv.Optional(CONF_PROXY): PROXY_SCHEMA,
        cv.Optional(CONF_CLOCK): CLOCK_SCHEMA,
        cv.Optional(CONF_BUTTONS): BUTTONS_SCHEMA,
        cv.Optional(CONF_CONTROLS): CONTROLS_SCHEMA,
        cv.Optional(CONF_STATUS): text_sensor.text_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
        cv.Optional(CONF_VERSIONS): text_sensor.text_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
        cv.Optional(CONF_ERRORS): sensor.sensor_schema(accuracy_decimals=0, state_class=STATE_CLASS_TOTAL_INCREASING,
                                                      entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
    })
    .extend(cv.polling_component_schema("10s"))
    .extend(uart.UART_DEVICE_SCHEMA),
    _build,
    _proxy_sockets,
)


def _cpp_formula(formula):
    """live_fields.json formula (Python) -> C++ expression over M(address)."""
    e = re.sub(r"\{0x([0-9a-f]+)\}", r"M(0x\1)", formula)
    e = re.sub(r"\{scale:(\w+)\}", lambda m: "M(0x%x)" % (SCALE_BASE + SCALES.index(m.group(1))), e)
    e = re.sub(r"\b(s16|u32|s32)\(", r"sppro::\1(", e)
    e = re.sub(r"\bmax\(", "sppro::smax(", e)
    e = re.sub(r"\babs\(", "std::fabs(", e)
    e = re.sub(r"\bsqrt\(", "std::sqrt(", e)
    if re.search(r"[{}]", e):
        raise cv.Invalid("cannot translate formula %r" % formula)
    return "[](const esphome::sppro::Mem &M) -> double { return %s; }" % e


def _c_string(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def _blocks_for(entities):
    """SP LINK's read blocks that cover the chosen fields' words (same ranges SP LINK reads)."""
    want = set()
    for e in entities:
        f = FIELDS[e[CONF_KEY]]
        blocks = [(int(a, 16), n) for a, n in TABLE["blocks"].get(f["screen"], [])]
        for w in [int(a, 16) for a in f["words"]] + list(range(SCALE_BASE, SCALE_BASE + len(SCALES))):
            hit = [b for b in blocks if b[0] <= w < b[0] + b[1]]
            if hit:
                want.add(hit[0])
    want.add((VERSION_BASE, VERSION_WORDS))
    if not any(b <= SCALE_BASE and SCALE_BASE + len(SCALES) <= b + n for b, n in want):
        want.add((SCALE_BASE, len(SCALES)))
    # drop blocks lying inside another one
    return sorted(b for b in want if not any(o != b and o[0] <= b[0] and b[0] + b[1] <= o[0] + o[1] for o in want))


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    cg.add(var.set_password(config[CONF_PASSWORD]))
    cg.add(var.set_timeout(config[CONF_TIMEOUT]))
    cg.add(var.set_expected_versions(*VERIFIED_VERSIONS))
    cg.add(var.set_allow_version_mismatch(config[CONF_ALLOW_VERSION_MISMATCH]))

    all_entities = [e for u in config["_units"] for e in u["_entities"]] + config["_system"]
    polled = list(all_entities)
    if CONF_CONTROLS in config:
        polled += [{CONF_KEY: k} for k in CONTROL_KEYS]
    for base, n in _blocks_for(polled):
        cg.add(var.add_block(base, n))
    cg.add(var.set_multi(config["_multi"]))

    tables_done = set()

    def enum_table(f):
        """Emit the enum's lookup table once; return (table expr, length expr)."""
        table = f["table"]
        if table not in tables_done:
            tables_done.add(table)
            rows = sorted((int(k), v) for k, v in ENUMS.get(table, {}).items() if k.lstrip("-").isdigit())
            body = ", ".join("{%d, %s}" % (k, _c_string(v)) for k, v in rows) or "{0, nullptr}"
            cg.add_global(cg.RawStatement(
                "static const esphome::sppro::EnumEntry sppro_table_%s[] = {%s};" % (table, body)))
            cg.add_global(cg.RawStatement(
                "static const size_t sppro_table_%s_len = %d;" % (table, len(rows))))
        return cg.RawExpression("sppro_table_%s" % table), cg.RawExpression("sppro_table_%s_len" % table)

    async def add_field(e, add_num, add_en):
        f = FIELDS[e[CONF_KEY]]
        fn = cg.RawExpression(_cpp_formula(f["formula"]))
        if f["kind"] == "enum":
            ts = await text_sensor.new_text_sensor(e)
            t, length = enum_table(f)
            add_en(ts, fn, t, length)
        else:
            s = await sensor.new_sensor(e)
            add_num(s, fn)

    if not config["_multi"]:                     # single inverter: the primary sensor lists, no re-addressing
        for e in config["_units"][0]["_entities"]:
            await add_field(e, lambda s, fn: cg.add(var.add_number(s, fn)),
                            lambda ts, fn, t, length: cg.add(var.add_enum(ts, fn, t, length)))
    else:                                        # Powerchain: one addressed unit per block, + the System totals
        for uid, u in enumerate(config["_units"]):
            cg.add(var.add_unit(uid, PHASES[u[CONF_PHASE]], ROLES[u[CONF_ROLE]], u[CONF_SERIAL]))
            for e in u["_entities"]:
                await add_field(
                    e,
                    (lambda i: lambda s, fn: cg.add(var.add_unit_number(i, s, fn)))(uid),
                    (lambda i: lambda ts, fn, t, length: cg.add(var.add_unit_enum(i, ts, fn, t, length)))(uid))
        for e in config["_system"]:
            f = FIELDS[e[CONF_KEY]]
            fn = cg.RawExpression(_cpp_formula(f["formula"]))
            s = await sensor.new_sensor(e)
            agg = Agg.SUM if _aggregation(f["unit"], f["key"]) == "sum" else Agg.AVG
            cg.add(var.add_system_number(s, fn, agg))

    for key, setter in ((CONF_STATUS, var.set_status_sensor), (CONF_VERSIONS, var.set_versions_sensor)):
        if key in config:
            cg.add(setter(await text_sensor.new_text_sensor(config[key])))
    if CONF_ERRORS in config:
        cg.add(var.set_errors_sensor(await sensor.new_sensor(config[CONF_ERRORS])))

    if CONF_CLOCK in config:
        c = config[CONF_CLOCK]
        cg.add_define("USE_SPPRO_CLOCK")
        rtc = await cg.get_variable(c[CONF_TIME_ID])
        cg.add(var.set_clock(rtc, c[CONF_INTERVAL], c[CONF_MAX_DRIFT].total_seconds, c[CONF_SET]))
        if CONF_DRIFT in c:
            cg.add(var.set_clock_drift_sensor(await sensor.new_sensor(c[CONF_DRIFT])))

    if CONF_BUTTONS in config or CONF_CONTROLS in config:
        cg.add_define("USE_SPPRO_BUTTONS")
    if CONF_CONTROLS in config:
        cg.add_define("USE_SPPRO_CONTROLS")
        c = config[CONF_CONTROLS]
        for key, which in CONTROLS.items():
            if key in c:
                sw = await switch.new_switch(c[key])
                await cg.register_parented(sw, var)
                cg.add(sw.set_which(which))
                cg.add(var.set_control_switch(which, sw))
        if "equalise" in c:
            b = await button.new_button(c["equalise"])
            await cg.register_parented(b, var)
            cg.add(b.set_which(3))
    if CONF_BUTTONS in config:
        for key, which in BUTTONS.items():
            if key in config[CONF_BUTTONS]:
                b = await button.new_button(config[CONF_BUTTONS][key])
                await cg.register_parented(b, var)
                cg.add(b.set_which(which))

    if CONF_PROXY in config:
        p = config[CONF_PROXY]
        socket.require_tcp_listener()
        cg.add_define("USE_SPPRO_PROXY")
        cg.add(var.set_proxy_port(p[CONF_PORT]))
        cg.add(var.set_proxy_log_downloads(p[CONF_LOG_DOWNLOADS]))
        connect = list(p.get(CONF_ALLOWED_IPS) or []) + [n for n in p[CONF_WRITE_IPS]
                                                         if n not in (p.get(CONF_ALLOWED_IPS) or [])]
        # an empty connect list would let anyone in, so always emit one when writers are listed
        socket.add_ipv4_allow(var.set_proxy_allow, connect, config[CONF_ID])
        if p[CONF_WRITE_IPS]:
            socket.add_ipv4_allow(var.set_proxy_write_allow, p[CONF_WRITE_IPS], "%s_write" % config[CONF_ID])
