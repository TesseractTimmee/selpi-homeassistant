# Changelog

## 0.4.9
- Four new default sensors from selpi's field table: **AC source power in / out** and **Battery power in / out**,
  the SP PRO's signed powers split into >= 0 parts (the SP PRO reports import and charging as negative). Use these
  for charts and statistics: averaging the signed values nets the two directions out.
- **Grid power in / out** and **Generator power in**: the AC source split by what it is, counted only while the
  inverter is synchronised to it (Output Mode Sync) and Generator Status says grid (AC Source Present) or
  generator (Running); 0 otherwise. The original AC source sensors stay. The ESPHome component gets all of these
  too (same table; 49 default entities).
- App: selpi v0.4.9. Integration unchanged apart from the version.

## 0.4.8
- Integration fix: setup failed ("Unique id ..._days_to_equalise is already in use") when the app was updated
  before the integration, because the older integration had already made a second entity for the renamed key
  (e.g. sensor.sp_pro_days_to_equalise_2). That duplicate is now removed and the original entity takes the new
  key, keeping its entity id and history. App unchanged (selpi v0.4.7).

## 0.4.7
- State-aware controls (selpi `sppro/controls.py`, `/api/v1/control`): a **Generator** switch and an
  **Inverter output** switch whose state is the SP PRO's own (Generator Status / Output Mode), so they show
  starts and stops from anything (state of charge, schedule, remote input, front panel). Switching reads the
  unit's state first and presses the button only when that changes something; the generator is refused
  with the grid present, disabled, faulted or out of fuel. They replace the "Generator start/stop" and
  "Inverter ON/IDLE (long press)" buttons (delete those once they show as unavailable). Inverter output is
  disabled by default and turning it off (IDLE, no AC output) asks for a second turn-off within 30 s.
- **Request equalise** button: two long Generator presses (SP PRO manual); the unit equalises after the
  next full charge. New default sensors: Days to equalise, Days since equalise, Generator started by.
- Field keys `daysto_recharge` / `daysto_equalise` renamed `days_to_recharge` / `days_to_equalise`
  (existing entities are moved to the new keys; the old keys still work in the API and in ESPHome `fields:`).
- ESPHome component: the same as `controls:` (generator / output switches, equalise button).

## 0.4.6
- ESPHome component: front panel buttons (`buttons:` generator, silence, and the protected `on_idle`), so the
  ESP can run Home Assistant on its own; the app is then only needed for backups, log downloads and the
  settings browser. `tools/sync_fields.sh` keeps the ESP's field tables in step with the app's selpi.
- README: which parts you need (ESP only, app + integration, ESP + app). App and integration unchanged
  apart from the version (selpi v0.4.6: protocol docs only).

## 0.4.5
- "Inverter ON/IDLE (long press)" button: the SP PRO ON button's long press, which switches the inverter
  between ON and IDLE (IDLE = no AC output, an outage). Protected: disabled until you enable it, and the first
  press only asks you to press again within 30 s. The app refuses it without an explicit confirmation.
  (selpi v0.4.5)

## 0.4.4
- Front panel buttons: the integration gets "Generator start/stop" and "Silence alarm" buttons, pressed the
  way SP LINK's Quick View front panel does (short press; shows in the SP PRO event log as a front panel
  press). Generator: starts/stops the auto start generator when off grid (on grid the press is logged and
  ignored). The ON button (ON <-> IDLE) is not offered. (selpi v0.4.4)

## 0.4.3
- Log downloads show a progress bar: which log, records read of total, percent and elapsed time;
  "SP PRO is searching" and "waiting for the SP PRO link" while those take time; a note if the page
  loses contact with the app. (selpi v0.4.3)

## 0.4.2
- Announce the app to Home Assistant only once its API answers, so the integration picks up a new or
  moved install straight away (before, it could miss it until the next HA restart).

## 0.4.0
- Optional SP LINK proxy: SP LINK reaches the SP PRO through this app, sharing its connection
  (off by default, read-only unless allowed, LAN only, one client).
- Import of install id, API token and backups from an earlier install (`/share/selpi-migrate`).
- Icon and logo; fixed labels ("Days to Recharge/Equalise", "AC Solar kWh …").
- First release from GitHub (selpi itself comes from TesseractTimmee/selpi at the same version tag).
