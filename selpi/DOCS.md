# selpi

Web page (sidebar "SP PRO") for the Selectronic SP PRO, without SP LINK or the Windows VM:

- **Live**: every value SP LINK's data screens show (Now, Today, Technical, history, service).
- **Configuration**: the settings laid out like SP LINK's Configuration Settings screens (same tabs and
  groups, values in SP LINK's units and pick-lists, SP LINK's ranges), searchable; a raw list too.
  Changes are checked with SP LINK's rules as you make them; writing them needs `allow_config_writes`.
- **Backups**: daily config backup (SP LINK `.SPLC` + service settings CSV + JSON), keep N, compare any two.
- **Logs**: events, alerts, daily summary, detailed data as SP LINK-format CSVs (zip).

It changes settings only from the Configuration page, and only with `allow_config_writes: true`. It can press the SP PRO's front panel buttons for the Home Assistant
integration, as SP LINK's Quick View front panel does: Generator start/stop and Silence alarm (short press),
and the ON button's long press (ON <-> IDLE; the integration's button for it is disabled by default and asks
for a second press within 30 s, because IDLE cuts the AC output).

A log download writes the SP PRO's download-mode and log-search registers,
as SP LINK does, and waits if someone else (SP LINK, the installer via Select.Live) is downloading.

## Connection
- `select_live`: through Select.Live (slower; the installer's path stays as it is).
- `tcp`: raw SP PRO frames over TCP: the ESPHome SP PRO USB link (`sppro`, port 8899; HA is read-only
  there, log downloads allowed) or any transparent serial-to-network bridge on the SP PRO's serial port.
- `serial`: a serial/USB device on the HA machine (`serial_device`, `serial_baudrate`; the SP PRO's
  serial port runs at 57600).

## Configuration writes
**Disabled in this release (read-only).** Writes are implemented and tested against a simulator but not yet validated against a real SP PRO, so this build shows the configuration but does not change it. The Configuration page is a viewer and `allow_config_writes` has no effect yet; a later release will enable writes once validated on hardware. When enabled, writes will work as follows:
Off by default. With `allow_config_writes: true` the Configuration page can write changed settings:

- it checks the changes with SP LINK's own rules and send checks (for example one function per input,
  voltage limits in order, frequency changes only in IDLE) and SP LINK's ranges, and refuses on an error
  unless you tick the override;
- the unit must be on the verified firmware versions, not busy (no log download or SP LINK write), and
  unchanged since the page read it (read again if it was changed meanwhile, e.g. from the front panel);
- it asks for the SP LINK passcode every time and never stores it;
- it saves a full backup first (`/data/config-writes`, SP LINK `.SPLC` + JSON), writes every change in one
  unlock session, always relocks, then reads the whole configuration back and reports anything else that
  changed.

Over the ESPHome link (`tcp`) the ESP forwards writes only from addresses in its proxy's `write_ips`
(`allowed_ips` clients may only make the writes a log download needs): put Home Assistant's address in
`write_ips` to write the configuration from here.

## Clock sync
`clock_sync: true` checks the SP PRO clock hourly and sets it to HA's time when it is more than
`clock_max_drift` seconds out. Leave it off when the ESPHome link does this (`clock:` in its config).

`sppro_password` is the SP PRO login password. Backups live in the app's `/data` (included in HA backups).

## Home Assistant integration
The app serves an API on port 8100 for the selpi integration, which turns the SP PRO into a normal HA
device with sensors. Install the integration from Marketplace (add
`https://github.com/TesseractTimmee/selpi-homeassistant` as a custom repository, type Integration).
Once it is installed, HA offers
"SP PRO discovered" under Settings > Devices & services. The API needs the token in the app's
`/data/api_token`; it is only reachable inside HA's internal network unless you map port 8100.
The integration polls every 60 s over Select.Live and every 10 s over serial or TCP (change it
under the integration's Configure).

## SP LINK proxy (optional)

Lets Selectronic's SP LINK (or any program that talks to the SP PRO's serial protocol) reach the SP PRO
*through this app*, sharing the app's connection. Useful when the SP PRO is on USB/serial on the Home
Assistant machine, or behind the ESP, and you still want SP LINK for commissioning or diagnostics.

1. Turn on **proxy** in the app's Configuration.
2. In the app's **Network** settings, give "SP LINK proxy" a host port (for example 8899), then restart the app.
3. In SP LINK, connect over TCP/IP to your Home Assistant's address and that port. Use the SP PRO's
   normal password; SP LINK logs in itself.

How it behaves:
- SP LINK's requests are passed to the SP PRO one at a time, between the app's own requests, so live values,
  backups and the integration keep working while SP LINK is connected. The integration's "Link status"
  may show `busy: SP LINK (…)` briefly.
- **Read-only by default.** Setting changes from SP LINK are refused (SP LINK reports a communication
  error for them) unless the computer running SP LINK is listed in **proxy_write**. Log downloads still work
  read-only (they need two small writes, which are allowed). Leave proxy_write empty unless you need to
  change settings from SP LINK.
- **proxy_allowed** lists who may connect (addresses or networks like `192.168.1.0/24`); empty means any
  private (LAN) address. Turn off **proxy_log_downloads** to also refuse log-download writes.
- One SP LINK at a time.
- Over **Select.Live** every request is a round trip to Selectronic's cloud (1–2 s), so SP LINK is slow
  and may time out. It works best with the USB/serial or ESP connection.
- The app's diagnostics (`/api/v1/diagnostics`) show who is connected and how many frames, refused writes
  and failures there have been.

## Moving from another install
To keep the integration's device (and its entities) and your config backups when replacing an earlier
selpi install (for example a local copy), put the old install's `install_id`, `api_token` and
`backups/` into `/share/selpi-migrate/` before the first start. The app imports them once and renames
the folder to `selpi-migrate.imported-<date>`. Stop the old install first so only one talks to the SP PRO.
