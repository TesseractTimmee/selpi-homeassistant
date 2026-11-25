"""
Shared presentation layer for SP PRO live fields: the display name, the HA entity hints
(device_class / state_class / display precision / category) and which same-quantity duplicate
readings to drop. Pure standard library, with no selpi or esphome imports.

Imported by the selpi app (sppro/live.py, web/api.py) and -- synced in by the HA repo's
tools/sync_fields.sh -- by the ESPHome component (esphome/components/sppro/__init__.py), so the
integration entities and the ESP firmware sensors are presented identically. Keep it dependency-free
so both can import it: this is the single source of truth, edit it here only.
"""
import re

# --- display name --------------------------------------------------------------------------------
# SP LINK's own labels are Title Case ("Battery Volts", "AC Generator RMS Amps") but the hand-picked
# defaults were sentence case ("Load power"), so entity lists read inconsistently. Normalise to Title
# Case (HA's usual device style), preserving SP PRO acronyms and units.
_ACRONYMS = {'AC', 'DC', 'RMS', 'SOC', 'PCA', 'PM', 'RD', 'PV', 'RTU', 'DTR', 'DCD', 'OEM', 'LED', 'DRM',
             'MPPT', 'BMS', 'ID', 'IP', 'KW', 'KWH', 'KVA', 'KVAR', 'WH', 'AH', 'HZ', 'VA'}
_ACRONYM_CANON = {'SOC': 'SoC', 'KW': 'kW', 'KWH': 'kWh', 'KVA': 'kVA', 'KVAR': 'kvar', 'WH': 'Wh',
                  'AH': 'Ah', 'HZ': 'Hz'}


def display_name(name):
    """SP LINK's label in Title Case, acronyms and units preserved. Idempotent on already-clean names."""
    name = name.replace('SPLINK', 'SP LINK')
    name = re.sub(r'\bL (\d)\b', r'L\1', name)          # split phase label "L 1" -> "L1"
    out = []
    for w in name.split():
        up = w.upper()
        if up in _ACRONYMS:
            out.append(_ACRONYM_CANON.get(up, up))
        elif re.fullmatch(r'L\d', w):                  # phase L1/L2/L3
            out.append(w.upper())
        elif not w.isalpha():                          # numbers, codes like "5min"
            out.append(w)
        else:
            out.append(w[0].upper() + w[1:].lower())   # Title Case each significant word
    return ' '.join(out)


# SP LINK labels needing a correction the curated defaults don't already make: how-it's-computed noise
# or an awkward word order. key -> final name (still Title-cased by field_name()).
NAME_OVERRIDES = {
    'now_ac_power_kaco1': 'AC Solar Power 1', 'now_ac_power_kaco2': 'AC Solar Power 2',
    'now_ac_power_kaco3': 'AC Solar Power 3', 'now_ac_power_kaco4': 'AC Solar Power 4',
    'now_ac_power_kaco5': 'AC Solar Power 5',
    'battery_volts_in_tech_tab': 'Battery Voltage',       # tech-tab twin of battery_volts; shown on web only
}


def field_name(key, splink_label, default_name=None):
    """Final display name for a field: override > curated default > SP LINK label, then Title-cased."""
    return display_name(NAME_OVERRIDES.get(key) or default_name or splink_label)


# --- HA / ESP entity hints -----------------------------------------------------------------------
# unit -> (device class or None, display precision). HA's reactive/apparent-power device classes only
# accept var / VA, not kvar / kVA, so those get no device class (HA would reject the unit and warn).
UNITS = {
    'kW': ('power', 3), 'kWh': ('energy', 2), 'kvar': (None, 3), 'kVA': (None, 3),
    'V': ('voltage', 1), 'A': ('current', 1), 'Hz': ('frequency', 2), '°C': ('temperature', 1),
    'h': ('duration', 1), '%': (None, 1), '': (None, 2),
}


# Identity / factory info that belongs in HA's Diagnostic section (and a web "Unit info" group) rather than the
# main readings. The raw serial/model fields already come through as diagnostics (kind == 'raw' below); this set
# adds the non-raw ones (e.g. firmware version). Batteryless (0xa021) and the factory export limit (0xa0aa)
# are now pinned (from the Select.Live capture) and surfaced as raw diagnostics; connected phase / comms-card serial
# can be added the same way.
DIAGNOSTIC = {'version_number', 'kaco_mode',
              'unit_model_number', 'unit_model_ratings', 'unit_rev_number'}   # device identity (product + hw rev)


def hints(f):
    """Entity hints for a field: {device_class, state_class, precision, category}."""
    cat = 'diagnostic' if f['key'] in DIAGNOSTIC else None
    if f['kind'] == 'enum':
        return {'device_class': 'enum', 'state_class': None, 'precision': None, 'category': cat}
    if f['kind'] == 'raw':
        # A raw field whose formula yields text (e.g. "'Yes' if ... else 'No'", "'No factory limit'") must not be
        # a measurement sensor — HA rejects a string value for state_class=measurement and the entity goes
        # unavailable. Only number-valued raw fields get the measurement class.
        text = "'" in f.get('formula', '') or '"' in f.get('formula', '')
        return {'device_class': None, 'state_class': None if text else 'measurement',
                'precision': None if text else 0, 'category': 'diagnostic'}
    dc, prec = UNITS.get(f['unit'], (None, 2))
    if f['unit'] == '%' and 'soc' in f['key']:
        dc = 'battery'
    sc = 'measurement'
    if f['unit'] == 'kWh':
        key = f['key']
        if 'avg' in key or 'previous' in key:
            sc = 'measurement'           # an average / last-period snapshot, not an accumulating meter
        elif 'net' in key:
            sc = 'total'                 # bidirectional: can go down, so total (not total_increasing)
        else:
            sc = 'total_increasing'      # a real energy meter (today / lifetime / accumulator)
    elif f['unit'] == 'h' and f['key'].endswith('_acc'):
        sc = 'total_increasing'
    return {'device_class': dc, 'state_class': sc, 'precision': prec, 'category': cat}


# --- same-quantity duplicates to drop from HA / ESP ----------------------------------------------
# SP LINK shows these on a second screen with a different register/formula, so the (words, formula)
# de-dup misses them. Keep the curated/named twin, drop the bare one (the web Live page still shows
# both, per screen). battery: keep battery_volts; inverter RMS = "Load Voltage": keep the tech twin,
# drop the unnamed main; charge status: keep the Now reading. Verify the pairs equal on hardware.
HA_DROP = {'battery_volts_in_tech_tab', 'ac_inverter_rms_volts', 'charge_status'}
