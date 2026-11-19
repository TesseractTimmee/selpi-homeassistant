# ESPHome firmware for the SP PRO link (USB, or the DB9 serial port: untested)

`components/sppro` is an ESPHome external component that talks to a Selectronic SP PRO over its own
protocol (the one SP LINK uses), logs in, reads the same memory blocks SP LINK's data screens read,
and publishes sensors to Home Assistant through the ESPHome API. No Modbus, no MQTT.

- Field table: `components/sppro/live_fields.json` / `splink_tables.json`, copies of selpi's
  (`sppro/` in the selpi fork, matching SP LINK 15.40, memory map 31). Run `tools/sync_fields.sh`
  after selpi's tables change.
- Version gate: every cycle reads the unit's version block (`0xa007`). If config/service/map/log
  versions are not 48/14/31/3/3/5 (what the table was checked against), nothing is published and
  "Link status" says "version mismatch" (override: `allow_version_mismatch: true`).
- Proxy (optional): a TCP port passing raw frames to the SP PRO for selpi or SP LINK, one client at a
  time, interleaved with polling. `allowed_ips` may connect read-only (login frames pass);
  `write_ips` may also write (SP LINK). Unlisted addresses are rejected. IPv4 only. SP LINK: TCP/IP
  mode, host = the ESP, port 8899 (it sends the same raw frames as over serial).
- Buttons (optional, `buttons:`): the SP PRO front panel buttons, pressed as SP LINK's Quick View does
  (the unit logs "... Button - Port N - Short Press"): `generator` (short: start/stop the auto start
  generator), `silence` (short: silence the alarm), `on_idle` (the ON button's long press: ON <-> IDLE,
  IDLE = no AC output; disabled by default in HA and needs a second press within 30 s). Avoid `/` in names.
- Clock (optional, `clock:`): checks the SP PRO clock every `interval` and sets it from SNTP when it is
  more than `max_drift` out; "Clock Drift" sensor. Leave the app's `clock_sync` off when this is on.
- Controls (optional, `controls:`), state-aware (selpi `sppro/controls.py`): `generator` and `output`
  switches show the unit's own state (Generator Status / Output Mode, whatever started or stopped it);
  switching reads the state fresh and presses Generator (short) / ON (long) only if that changes
  something, never twice for a press the unit hasn't shown yet (30 s). The generator is refused with the
  grid present, disabled, faulted or out of fuel. `output` off = IDLE (no AC output): disabled by default
  and needs a second request within 30 s. `equalise`: a button for the equalise request (two long
  Generator presses; the SP PRO equalises after the next full charge). These switches never act at boot
  (`restore_mode` must stay `DISABLED`).
- Entities: 42 by default (powers, voltages, SoC, temperatures, today's energies, status texts, digital inputs 1–4), plus
  Link status / Unit versions / Link errors. Choose others with `fields:` (keys from
  `selpi live --list`), each a key or `{key: ..., name: ..., <sensor options>}`; `all_fields: true`
  adds all 288.

## Files
- `sppro.yaml` + `includes/esp32s3-usb-otg.yaml`: an example device (ESP32-S3-USB-OTG + ADuM3160 USB
  isolator, USB CDC Microchip 04D8:000A), using shared `api_password` / wifi / `ap_password` secrets,
  OTA encryption, SNTP and diagnostics, plus `sppro_password` and the proxy addresses
  (`secrets.yaml.example`).
- `sppro-serial.yaml` (**untested**): the same component on the SP PRO's DB9 serial port (comms port 1)
  through an RS-232 converter (MAX3232) on a plain ESP32's UART. See "Serial port" below.
- `components/sppro`: the component. `sppro.yaml` pulls it from this repository at a version tag. Its field
  tables come from the selpi fork (`tools/sync_fields.sh`).
- `sppro-sim.yaml`: host build against selpi's simulator (TesseractTimmee/selpi, `tools/sim_sppro.py`),
  for testing without hardware.

## Installing
1. Copy `sppro.yaml` and `includes/esp32s3-usb-otg.yaml` into your ESPHome config folder
   (in Home Assistant: `/config/esphome/`).
2. Add the keys from `secrets.yaml.example` to your ESPHome `secrets.yaml`.
3. In the ESPHome Device Builder: Install (first time over USB-C, then OTA).
4. In the selpi app, set the connection to `tcp`, host = the ESP, port 8899.

## Serial port (untested)
Nobody has run `sppro-serial.yaml` on a real unit yet; reports welcome. The component needs no changes (it
reads any UART), only the hardware and line settings differ from USB:
- The DB9 is RS-232 (about ±12 V): put an RS-232 converter (MAX3232 board, 3.3 V side) between it and the
  ESP's UART pins. Never connect it directly.
- It is the port a Select.Live device uses; the two can't share it. Use USB if Select.Live is plugged in.
- Line settings: 57600 8N1 assumed (selpi's setting for USB-serial units); check the SP PRO manual.
- If Link Status stays on "connecting" or "login failed: no reply", swap TX and RX (straight vs null-modem wiring).
- Front panel buttons work the same; on this port the unit uses its port 1 button registers.
