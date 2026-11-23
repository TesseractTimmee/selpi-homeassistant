# selpi

A web page (sidebar **SP PRO**) for the Selectronic SP PRO — everything SP LINK does, without SP LINK or a
Windows VM:

- **Live** — every value SP LINK's data screens show (Now, Today, Technical, history, service).
- **Configuration** — the settings laid out like SP LINK's Configuration Settings screens (same tabs and
  groups, SP LINK's units, pick-lists and ranges), searchable, with a raw list too. Changes are checked
  against SP LINK's rules as you make them; writing them needs `allow_config_writes` (see below).
- **Backups** — a daily config backup (SP LINK `.SPLC` + service-settings CSV + JSON); keep the newest N,
  compare any two, delete one.
- **Logs** — events, alerts, daily summary and detailed data as SP LINK-format CSVs (zipped).

The page only writes settings from the **Configuration** page, and only with `allow_config_writes: true`.
It can also press the SP PRO's front-panel buttons for the Home Assistant integration, the way SP LINK's
Quick View panel does: Generator start/stop and Silence alarm (short press), and the ON button's long press
(ON ↔ IDLE — the integration's button for it is disabled by default and asks for a second press within 30 s,
because IDLE cuts the AC output).

A log download writes the SP PRO's download-mode and log-search registers, as SP LINK does, and waits if
something else (SP LINK, or the installer via Select.Live) is already downloading.

## Connection
- **`select_live`** — through Select.Live (slower; the installer's own path is unaffected).
- **`tcp`** — raw SP PRO frames over TCP: the ESPHome SP PRO USB link (`sppro`, port 8899; read-only from HA,
  log downloads allowed), or any transparent serial-to-network bridge on the SP PRO's serial port.
- **`serial`** — a serial/USB device on the HA machine (`serial_device`, `serial_baudrate`; the SP PRO's
  serial port runs at 57600).

## Configuration writes
**Read-only in this release.** Writes are implemented and tested against a simulator but not yet validated on
real hardware, so this build *shows* the configuration but does not change it — the Configuration page is a
viewer and `allow_config_writes` has no effect yet. A later release enables writes once validated on an SP PRO.

When enabled, writes will work like this (off by default; `allow_config_writes: true` turns them on):

- each change is checked against SP LINK's own rules and send-checks (e.g. one function per input, voltage
  limits in order, frequency changes only in IDLE) and SP LINK's ranges, and is refused on an error unless you
  tick the override;
- the unit must be on a verified firmware version, not busy (no log download or SP LINK write in progress),
  and unchanged since the page last read it (if it changed meanwhile — e.g. from the front panel — read again);
- it asks for the SP LINK passcode every time and never stores it;
- it saves a full backup first (`/data/config-writes`, `.SPLC` + JSON), writes every change in one unlock
  session, always relocks, then reads the whole configuration back and reports anything else that changed.

Over the ESPHome link (`tcp`), the ESP forwards writes only from addresses in its proxy's `write_ips`
(`allowed_ips` clients may only make the small writes a log download needs). Put Home Assistant's address in
`write_ips` to write the configuration from here.

## Clock sync
`clock_sync: true` checks the SP PRO clock hourly and sets it to HA's time when it drifts more than
`clock_max_drift` seconds. Leave it off if the ESPHome link already does this (its own `clock:` config).

`sppro_password` is the SP PRO login password. Backups live in the app's `/data` (included in HA backups).

## Caching
The Configuration/Settings pages and the live values are cached, so a slow or stalled Select.Live link
doesn't hang the UI or make the integration's entities flap. The defaults follow the connection and need no
setup — **Select.Live caches; a direct link (serial, or a local TCP/ESP link) reads fresh.** Two options
override that:

- **`cache_ttl`** (seconds) — how long the Configuration/Settings page may be served from the last read
  before re-reading the link. `0` = always read fresh (a read error still falls back to the last good read).
- **`stale_grace`** (seconds) — how long the last live value is served after the link fails, before a poll
  returns nothing (so the integration can mark entities unavailable). `0` = never serve stale — entities go
  "unknown" as soon as the link drops (good on a reliable local link). The integration's own `grace` option
  (under **Configure**) defaults from this and decides how long before entities go unavailable.

Set both above `0` for a TCP link that is genuinely remote/slow (not a local ESP) to get Select.Live-style
resilience over it.

## Home Assistant integration
The app serves an API on port **8100** for the selpi integration, which turns the SP PRO into a normal HA
device with sensors (and is where you build history, energy dashboards or an InfluxDB/Grafana feed — through
HA, like any other device). Install the integration from **Marketplace** (add
`https://github.com/TesseractTimmee/selpi-homeassistant` as a custom repository, type *Integration*); HA then
offers **"SP PRO discovered"** under *Settings → Devices & services*.

The API uses the token in `/data/api_token` and is only reachable inside HA's internal network unless you map
port 8100. The integration polls every 60 s over Select.Live and every 10 s over serial or TCP (change it
under the integration's **Configure**).

## SP LINK proxy (optional)
Lets Selectronic's SP LINK (or anything that speaks the SP PRO's serial protocol) reach the SP PRO *through
this app*, sharing its connection — handy when the SP PRO is on USB/serial at the HA machine, or behind the
ESP, and you still want SP LINK for commissioning or diagnostics.

1. Turn on **proxy** in the app's Configuration.
2. In the app's **Network** settings, give "SP LINK proxy" a host port (e.g. 8899), then restart the app.
3. In SP LINK, connect over TCP/IP to your HA address and that port, with the SP PRO's normal password
   (SP LINK logs in itself).

How it behaves:

- SP LINK's requests are interleaved with the app's own, one at a time, so live values, backups and the
  integration keep working while SP LINK is connected. The integration's **Link status** may briefly show
  `busy: SP LINK (…)`.
- **Read-only by default.** Setting changes from SP LINK are refused (SP LINK reports a communication error)
  unless the computer running it is listed in **`proxy_write`**. Log downloads still work read-only (they need
  two small writes, which are allowed). Leave `proxy_write` empty unless you need to change settings from SP LINK.
- **`proxy_allowed`** lists who may connect (addresses or networks like `192.168.1.0/24`); empty = any private
  (LAN) address. Turn off **`proxy_log_downloads`** to also refuse the log-download writes.
- One SP LINK at a time.
- Over **Select.Live**, every request is a round trip to Selectronic's cloud (1–2 s), so SP LINK is slow and
  may time out — it works best over the USB/serial or ESP connection.
- The app's diagnostics (`/api/v1/diagnostics`) show who is connected, and the frame, refused-write and
  failure counts.

## Moving from another install
To keep the integration's device (and its entities) and your config backups when replacing an earlier selpi
install (e.g. a local copy), put the old install's `install_id`, `api_token` and `backups/` into
`/share/selpi-migrate/` before the first start. The app imports them once and renames the folder to
`selpi-migrate.imported-<date>`. Stop the old install first, so only one thing talks to the SP PRO.
