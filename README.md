# selpi for Home Assistant (Selectronic SP PRO)

Home Assistant app, integration and ESPHome component for the **Selectronic SP PRO** inverter, using its
own protocol (the one SP LINK uses). Built on [selpi](https://github.com/TesseractTimmee/selpi)
(fork of [neerolyte/selpi](https://github.com/neerolyte/selpi)).

| Part | Folder | What it does |
|---|---|---|
| **App** (Settings → Apps) | `selpi/` | Talks to the SP PRO via Select.Live, a TCP serial bridge / the ESPHome link, or USB/serial on the HA machine. Web page with every live value and setting, daily config backups, log downloads, clock sync, optional SP LINK proxy. API for the integration. |
| **Integration** (Marketplace) | `custom_components/selpi` | The SP PRO as an HA device: sensors for the live values (39 on by default, ~276 available), link status, clock drift, last backup, a backup button. Found automatically when the app runs. |
| **ESPHome component** | `esphome/` | ESP32-S3 on the SP PRO's USB port: local link without Select.Live, frame proxy for the app and SP LINK, clock sync. |

**Powerchain (multiple inverters):** each inverter appears as its own HA device ("L1 Manager", …) under a
**SP PRO System** roll-up device; the web dashboard gets a unit picker. Topology is read from the inverters
(assigned in SP LINK), read-only. See [the app docs](selpi/DOCS.md#powerchain-multiple-inverters) and the full
[field reference](selpi/FIELDS.md).

## Which parts you need

| Setup | Live sensors and buttons in HA | The app adds |
|---|---|---|
| **ESP only** | ESPHome device (sensors, front panel buttons, clock sync) | - |
| **App + integration** (Select.Live, serial on the HA machine, or a TCP serial bridge) | the integration | backups, log downloads, settings browser, clock sync, SP LINK proxy |
| **ESP + app** | ESPHome device | backups, log downloads, settings browser (the app connects through the ESP's proxy) |

With the ESP, skip the integration (or leave its entities disabled), or HA gets every sensor and button twice.

## Install
1. **App:** Settings → Apps → App store → ⋮ → Repositories → add
   `https://github.com/TesseractTimmee/selpi-homeassistant`, then install **selpi**, set the connection and
   the SP PRO password in its Configuration, start it. See the app's Documentation tab.
2. **Integration:** Marketplace → ⋮ → Custom repositories → add the same URL, type **Integration**,
   download **selpi**, restart Home Assistant. Then accept "SP PRO discovered" in Settings → Devices & services.
3. **ESPHome (optional hardware):** see [`esphome/README.md`](esphome/README.md).

Read-only by design: nothing here changes inverter settings (except the clock, when you turn clock sync on).

## Development
- Integration tests: `pytest` (needs `pytest-homeassistant-custom-component`).
- `tools/deploy_dev.sh`: copy the integration straight to a test HA over ssh (`HA=user@host`).
- `tools/sync_fields.sh`: refresh the ESPHome component's field tables from the selpi fork at `SELPI_REF`.
- The app pins selpi with `SELPI_REF` in `selpi/Dockerfile`; keep it and the versions in
  `selpi/config.yaml` and `custom_components/selpi/manifest.json` in step.

MIT licence (see `LICENSE.md`).
