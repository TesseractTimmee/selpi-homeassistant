"""
ESPHome external component: Selectronic SP PRO over its native link (USB CDC, or any UART stream).

Reads the same memory blocks SP LINK's data screens read and publishes chosen fields as sensors /
text sensors. The field table (live_fields.json, splink_tables.json) is selpi's, generated from
SP LINK 15.40's display code for memory map 31 (selpi/tools/splink/); keep the copies here in sync
with selpi/sppro/ (tools/sync_fields.sh in this repo).

Optional buttons: the SP PRO's front panel buttons as ESPHome buttons (generator start/stop and silence
alarm: short press; on_idle: the ON button's long press, ON <-> IDLE, disabled by default and needing a second press within 30 s),
pressed the way SP LINK's Quick View front panel does (see selpi docs/protocol.md).

Optional proxy: a TCP port that passes raw SP PRO frames (selpi, SP LINK) through, interleaved with
the component's own polling. Clients in `allowed_ips` are read-only (login frames pass); clients in `write_ips`
may also write (e.g. SP LINK).
"""
import json
import os
import re

import esphome.codegen as cg
from esphome.components import button, sensor, socket, text_sensor, time as time_, uart
import esphome.config_validation as cv
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
AUTO_LOAD = ["button", "sensor", "text_sensor", "md5", "socket"]

CONF_FIELDS = "fields"
CONF_ALL_FIELDS = "all_fields"
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
BUTTONS = {"generator": 0, "on_idle": 1, "silence": 2}   # "on" would be read as YAML true

_HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = json.load(open(os.path.join(_HERE, "live_fields.json"), encoding="utf-8"))
ENUMS = json.load(open(os.path.join(_HERE, "splink_tables.json"), encoding="utf-8"))
FIELDS = {f["key"]: f for f in TABLE["fields"]}
SCALES = ["AcVolts", "AcCurrent", "DcVolts", "DcCurrent", "Temperature", "InternalVoltages"]
SCALE_BASE = 0xA028
VERSION_BASE, VERSION_WORDS = 0xA007, 25
# config settings, service settings, memory map, event/detailed/daily log formats (0xa007..0xa00c).
# The field table was built and checked at these; see selpi docs/protocol.md "Version block".
VERIFIED_VERSIONS = [48, 14, 31, 3, 3, 5]

# A sensible default set (HA names), shared with the selpi add-on's HA API (sppro/default_fields.json).
# Any key from live_fields.json can be added under `fields:`.
DEFAULT_FIELDS = json.load(open(os.path.join(_HERE, "default_fields.json"), encoding="utf-8"))

# unit -> (device_class, accuracy)
UNITS = {
    "kW": ("power", 3), "kWh": ("energy", 2), "kvar": ("reactive_power", 3), "kVA": ("apparent_power", 3),
    "V": ("voltage", 1), "A": ("current", 1), "Hz": ("frequency", 2), "°C": ("temperature", 1),
    "h": ("duration", 1), "%": (None, 1), "": (None, 2),
}

sppro_ns = cg.esphome_ns.namespace("sppro")
SpPro = sppro_ns.class_("SpPro", cg.PollingComponent, uart.UARTDevice)
SpProButton = sppro_ns.class_("SpProButton", button.Button, cg.Parented.template(SpPro))


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
    if value[CONF_KEY] not in FIELDS:
        raise cv.Invalid("unknown SP PRO field '%s' (see live_fields.json, or `selpi live --list`)" % value[CONF_KEY])
    return value


def _entity_schema(f):
    if f["kind"] == "enum":
        return text_sensor.text_sensor_schema()
    if f["kind"] == "raw":
        return sensor.sensor_schema(accuracy_decimals=0, state_class=STATE_CLASS_MEASUREMENT,
                                    entity_category=ENTITY_CATEGORY_DIAGNOSTIC)
    device_class, acc = UNITS.get(f["unit"], (None, 2))
    if f["unit"] == "%" and "soc" in f["key"]:
        device_class = "battery"
    state_class = STATE_CLASS_MEASUREMENT
    if f["unit"] == "kWh":
        net = "net" in f["key"]
        state_class = STATE_CLASS_TOTAL_INCREASING if ("today" in f["key"] or f["key"].endswith("_acc")) and not net \
            else STATE_CLASS_TOTAL
    kw = dict(accuracy_decimals=acc, state_class=state_class)
    if f["unit"]:
        kw["unit_of_measurement"] = f["unit"]
    if device_class:
        kw["device_class"] = device_class
    return sensor.sensor_schema(**kw)


def _expand_fields(config):
    """Turn `fields:` (keys, or dicts with key + entity options) into validated entity configs."""
    entries = config.get(CONF_FIELDS)
    if entries is None:
        entries = [{CONF_KEY: k, CONF_NAME: n} for k, n in DEFAULT_FIELDS.items()]
    if config[CONF_ALL_FIELDS]:
        # every other field, minus exact repeats (same words and formula on another screen)
        seen = {(tuple(FIELDS[e[CONF_KEY]]["words"]), FIELDS[e[CONF_KEY]]["formula"]) for e in entries}
        for k, f in FIELDS.items():
            sig = (tuple(f["words"]), f["formula"])
            if sig not in seen and all(e[CONF_KEY] != k for e in entries):
                seen.add(sig)
                entries = entries + [{CONF_KEY: k, "_auto": True}]
    out, names = [], set()
    for e in entries:
        f = FIELDS[e[CONF_KEY]]
        conf = {k: v for k, v in e.items() if k not in (CONF_KEY, "_auto")}
        if CONF_NAME not in conf:
            name = f["name"]
            if _slug(name) in names:   # same label on two screens: say which
                name = "%s (%s)" % (name, SCREEN_NAMES.get(f["screen"], f["screen"]))
            if _slug(name) in names:
                name = "%s (%s)" % (f["name"], f["key"])
            conf[CONF_NAME] = name
        names.add(_slug(conf[CONF_NAME]))
        conf = _entity_schema(f)(conf)
        conf[CONF_KEY] = f["key"]
        out.append(conf)
    config = dict(config)
    config["_entities"] = out
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
    # ON <-> IDLE cuts the AC output: off in HA until enabled, and two presses within 30 s
    cv.Optional("on_idle"): button.button_schema(SpProButton, icon="mdi:power", entity_category=ENTITY_CATEGORY_CONFIG)
    .extend({cv.Optional("disabled_by_default", default=True): cv.boolean}),
})


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
        cv.Optional(CONF_FIELDS): cv.ensure_list(_field_entry),
        cv.Optional(CONF_ALL_FIELDS, default=False): cv.boolean,
        cv.Optional(CONF_ALLOW_VERSION_MISMATCH, default=False): cv.boolean,
        cv.Optional(CONF_PROXY): PROXY_SCHEMA,
        cv.Optional(CONF_CLOCK): CLOCK_SCHEMA,
        cv.Optional(CONF_BUTTONS): BUTTONS_SCHEMA,
        cv.Optional(CONF_STATUS): text_sensor.text_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
        cv.Optional(CONF_VERSIONS): text_sensor.text_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
        cv.Optional(CONF_ERRORS): sensor.sensor_schema(accuracy_decimals=0, state_class=STATE_CLASS_TOTAL_INCREASING,
                                                      entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
    })
    .extend(cv.polling_component_schema("10s"))
    .extend(uart.UART_DEVICE_SCHEMA),
    _expand_fields,
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

    for base, n in _blocks_for(config["_entities"]):
        cg.add(var.add_block(base, n))

    tables_done = set()
    for e in config["_entities"]:
        f = FIELDS[e[CONF_KEY]]
        fn = cg.RawExpression(_cpp_formula(f["formula"]))
        if f["kind"] == "enum":
            ts = await text_sensor.new_text_sensor(e)
            table = f["table"]
            if table not in tables_done:
                tables_done.add(table)
                rows = sorted((int(k), v) for k, v in ENUMS.get(table, {}).items() if k.lstrip("-").isdigit())
                body = ", ".join("{%d, %s}" % (k, _c_string(v)) for k, v in rows) or "{0, nullptr}"
                cg.add_global(cg.RawStatement(
                    "static const esphome::sppro::EnumEntry sppro_table_%s[] = {%s};" % (table, body)))
                cg.add_global(cg.RawStatement(
                    "static const size_t sppro_table_%s_len = %d;" % (table, len(rows))))
            cg.add(var.add_enum(ts, fn, cg.RawExpression("sppro_table_%s" % table),
                                cg.RawExpression("sppro_table_%s_len" % table)))
        else:
            s = await sensor.new_sensor(e)
            cg.add(var.add_number(s, fn))

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

    if CONF_BUTTONS in config:
        cg.add_define("USE_SPPRO_BUTTONS")
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
