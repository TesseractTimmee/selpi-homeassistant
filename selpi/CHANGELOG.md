# Changelog

## 0.6.4
- **One Configuration button.** 0.6.3 briefly added a second (refresh) button next to "Read configuration";
  since the tab already auto-loads the cached config on open, that was redundant. Back to a single
  "Read from SP PRO" button (always a fresh read); reopening the tab still serves the cached copy, no link read.

## 0.6.3
- **Configuration page is cached.** Opening/reopening the web UI's Configuration page no longer re-reads the
  whole config over the link every time — it serves the last read, so it's instant and doesn't starve the live
  poll or stall a slow Select.Live connection. A new ↻ (Refresh) button forces a fresh read; a successful write
  clears the cache so the next open re-reads the changed config. Live-data freshness is unchanged. (Pulls selpi
  app v0.6.3.)

## 0.6.2
- **Fix: non-default sensors no longer all enabled.** 0.6.0 introduced a bug where, with no ESP present, the
  integration re-enabled *every* sensor it had disabled — including the many infrequently-used (non-default)
  field sensors that are meant to be disabled by default — because Home Assistant marks both "disabled by
  default" and "disabled because the ESP is present" with the same `disabled_by=INTEGRATION`. The ESP
  show/hide now only touches the default (normally-enabled) sensors, and a one-time repair re-disables the
  non-default sensors the bug enabled (any you enable yourself afterwards stay enabled). (Integration only.)

## 0.6.1
- **Poll resilience over Select.Live.** Fixes the integration failing to load / the add-on sticking on
  "busy: HA poll" when the SP PRO is reached over a slow or flaky Select.Live link. The poll now reads each
  block independently and skips any that doesn't reply (reconnecting per block) instead of failing the whole
  poll, so a slow link returns partial/stale data rather than nothing; it's bounded by a 30 s deadline so a
  stuck block can't hold the link for minutes; and a field whose block was skipped keeps its last good value
  instead of being wiped. (Pulls selpi app v0.6.1.)
- Integration: the constant factory/firmware diagnostics are treated as static (fetched once, refreshed
  hourly) so they don't add their registers to every poll.

## 0.6.0
- **SP LINK 16.11 support.** Settings now match SP LINK 16.11: new managed-BMS battery types (AERL, XESS,
  SelectCell River Gum), the Fronius range rename (Verto), granular MPPT alert codes, and the CSIP fallback
  export-limit settings.
- **Fuller show/hide & read-only, like SP LINK.** Settings are gated on the SP PRO firmware / memory-map
  version, the Comms Card software version, and other settings' values (power factor, AC-coupling, SoC control,
  batteryless, Kaco port, external CT, shunt mode), and whole-group firmware hiding — so the web UI greys/hides
  the same fields SP LINK does. Installer/factory settings stay read-only.
- **Service Settings** are decoded and shown (read-only) in their own tab: AC-solar control gains, filters,
  anti-islanding, CSIP export limits, and more.
- **New diagnostics** (web Live page + HA Diagnostic): batteryless, factory export limit, Comms Card serial /
  software, Kaco mode / count, grid firmware, and a staged-firmware indicator — all pinned from the live link.
- **Connections:** Select.Live 2 is selectable (server presets: Select.Live / Select.Live 2 / nonprod, plus a
  manual host), alongside the existing Select.Live, serial and TCP (ESP proxy) options.
- **Integration — sensors no longer flap.** A brief add-on/link hiccup used to drop every sensor; the
  integration now keeps the last values through short failures and shows "retrying" on the Link status.
- **Integration — ESP aware.** Detects when the ESPHome component is the link (Connected via = ESP proxy) and
  hides the duplicate SP PRO data sensors, leaving the add-on's extras; warns if both the add-on and the ESP are
  set to sync the SP PRO clock. New "Connected via" sensor shows the transport.
- **ESP firmware:** an SP PRO status screen for the ESP32-S3-USB-OTG LCD.
- Still read-only: configuration writes remain disabled pending on-hardware validation.
- App: selpi v0.6.0.


## 0.5.4
- **Naming consistency.** The HACS/Marketplace listing now shows "Selectronic SP PRO" instead of
  "selpi (Selectronic SP PRO)" — that name came from hacs.json, not the manifest. Setup-dialog/error text that
  said "the selpi add-on" now says "the Selectronic SP PRO add-on". The domain and slug stay "selpi" (entity ids
  depend on them). No functional change.
- App: selpi v0.5.3 (unchanged).

## 0.5.3
- **Fixes the lockup/timeout when switching between Live and Configuration.** A stalled or flaky Select.Live
  link could hold the single SP PRO link for minutes (the configuration read retries across every block),
  leaving "configuration read…" stuck in the top-right and blocking the page and HA polls. Link operations now
  have a time budget and give up cleanly rather than wedging (live 25 s, settings 40 s, configuration 45 s).
- **Web UI:** requests time out after 90 s and show "try again" instead of spinning forever; a second
  configuration read no longer starts while one is in flight, so the double countdown-timer is gone.
- **Integration:** the constant identity values (model, serial, PCA/PM serials, firmware) are read once and
  refreshed occasionally instead of on every poll, trimming per-poll link load.
- Still read-only: configuration writes remain disabled pending on-hardware validation.
- App: selpi v0.5.3.

## 0.5.2
- **Consistent entity names and info.** Entity names are now Title Case and consistent across the app, the HA
  integration and the ESP firmware, driven by one shared source, so they no longer differ between them; a few
  names that showed an internal label or odd word order were fixed.
- **HA entity fixes.** kvar / kVA readings no longer get a device class HA rejects (they were logged as invalid);
  kWh averages and last-period snapshots are now plain measurements, so they stop appearing as Energy-dashboard
  meters (only real meters do).
- **Unit / factory info.** Model number, serial number, Control PCA and PM1/PM2 serials and firmware version are
  now shown as Diagnostic entities. (More factory values - batteryless, export limit, phase - come once their
  registers are confirmed on hardware.)
- **Inverter controls.** The Inverter ON/IDLE button and Inverter output switch now appear under Controls rather
  than Configuration; they are still disabled by default and still need a second press/toggle within 30 s to act.
- **Earlier UI fixes.** Detailed data-log interval reads "15 min" (not a code); schedule fields are grouped by
  schedule number; a valid setting value below SP LINK's editable minimum is shown without a false out-of-range flag.
- Still read-only: configuration writes remain disabled pending on-hardware validation.
- App: selpi v0.5.2.

## 0.5.1
- **Firmware-aware Configuration page:** each setting now knows the minimum SP PRO config-settings version SP LINK
  needs to show it; on older firmware the page shows those settings read-only with a "needs firmware vN" note
  (65 settings, e.g. the newer AC-scheduling, AC-coupling and Powerchain options). The page reads the unit's
  config version and adapts, so it's correct on any firmware, not just the one it was built against.
- **Powerchain (multi-phase):** the Powerchain Plan / Inverters per Phase / Balance 3 Phase settings are decoded
  and editable; they need config version 38, and a rule refuses a Powador string-inverter port with more than one
  inverter per phase. (Multi-unit structure/count checks that need the live detected-inverter list are not done.)
- Still read-only: configuration writes remain disabled pending on-hardware validation.
- App: selpi v0.5.1.

## 0.5.0
- **Configuration page (read-only):** a new "Configuration" tab in the web UI shows every setting the way SP LINK's
  Configuration Settings screens do — the same tabs, groups, units, pick-lists and ranges — with SP LINK's own
  validation shown live as you look. Replaces the old raw settings list (kept as a toggle).
- **Settings decoded from SP LINK (587):** meanings, units, ranges and SP LINK's rules, including per-battery-type DC
  voltage limits, power-factor settings, the Year-to-Date rollover date, the MPPT model list, and the AS4777 Region
  (previously mislabelled as a percent field).
- **Installer-only settings are read-only:** the 19 AS4777 grid-protection / Volt-Var / Volt-Watt / charge-voltage
  settings SP LINK keeps behind the installer code are shown but never written.
- **Faster Select.Live reads:** a lost reply is retried at once instead of after ~1 minute (a full configuration read
  is now a few seconds).
- `selpi config show` / `config set` show the value, unit, range and SP LINK screen location; dry-run previews.
- **Configuration writes are implemented but disabled in this release**, pending validation against a real SP PRO.
  The `allow_config_writes` option and `config set --yes` will enable them in a later release.
- App: selpi v0.5.0. Integration unchanged apart from the version.

## 0.4.10
- Grid / generator power: the generator now counts while the inverter is synchronised and the generator is in any
  generator state (Running, Starting: the two-stage start carries the loads before the charger, Stopping); the grid
  counts while synchronised in any other state. Before, the grid needed "AC Source Present", which units without a
  generator don't report. Same sensors, same history.
- selpi command line: `selpi config set NAME VALUE` (guarded one-setting writes; dry run without --yes).
- App: selpi v0.4.10. Integration unchanged apart from the version.

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
