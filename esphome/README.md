# ESPHome firmware for the SP PRO USB link

`components/sppro` is an ESPHome external component that talks to a Selectronic SP PRO over its own
protocol (the one SP LINK uses), logs in, reads the same memory blocks SP LINK's data screens read,
and publishes sensors to Home Assistant through the ESPHome API. No Modbus, no MQTT.

- Field table: `components/sppro/live_fields.json` / `splink_tables.json`, copies of selpi's
  (`../sppro/`, generated from SP LINK 15.40's display code, memory map 31). Run `./sync.sh` after
  regenerating them.
- Version gate: every cycle reads the unit's version block (`0xa007`). If config/service/map/log
  versions are not 48/14/31/3/3/5 (what the table was checked against), nothing is published and
  "Link status" says "version mismatch" (override: `allow_version_mismatch: true`).
- Proxy (optional): a TCP port passing raw frames to the SP PRO for selpi or SP LINK, one client at a
  time, interleaved with polling. `allowed_ips` may connect read-only (login frames pass);
  `write_ips` may also write (SP LINK). Unlisted addresses are rejected. IPv4 only. SP LINK: TCP/IP
  mode, host = the ESP, port 8899 (it sends the same raw frames as over serial).
- Entities: 39 by default (powers, voltages, SoC, temperatures, today's energies, status texts, digital inputs 1–4), plus
  Link status / Unit versions / Link errors. Choose others with `fields:` (keys from
  `selpi live --list`), each a key or `{key: ..., name: ..., <sensor options>}`; `all_fields: true`
  adds all 288.

## Files
- `sppro.yaml` + `includes/esp32s3-usb-otg.yaml`: an example device (ESP32-S3-USB-OTG + ADuM3160 USB
  isolator, USB CDC Microchip 04D8:000A), using shared `api_password` / wifi / `ap_password` secrets,
  OTA encryption, SNTP and diagnostics, plus `sppro_password` and the proxy addresses
  (`secrets.yaml.example`).
- `components/sppro`: the component. `sppro.yaml` pulls it from this repository at a version tag.
- `sppro-sim.yaml`: host build against selpi's simulator (TesseractTimmee/selpi, `tools/sim_sppro.py`),
  for testing without hardware.

## Installing
1. Copy `sppro.yaml` and `includes/esp32s3-usb-otg.yaml` into your ESPHome config folder
   (in Home Assistant: `/config/esphome/`).
2. Add the keys from `secrets.yaml.example` to your ESPHome `secrets.yaml`.
3. In the ESPHome Device Builder: Install (first time over USB-C, then OTA).
4. In the selpi app, set the connection to `tcp`, host = the ESP, port 8899.
