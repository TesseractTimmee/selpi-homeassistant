# selpi

Web page (sidebar "SP PRO") for the Selectronic SP PRO, without SP LINK or the Windows VM:

- **Live**: every value SP LINK's data screens show (Now, Today, Technical, history, service).
- **Settings**: all 623 configuration and service settings (raw values), searchable.
- **Backups**: daily config backup (SP LINK `.SPLC` + service settings CSV + JSON), keep N, compare any two.
- **Logs**: events, alerts, daily summary, detailed data as SP LINK-format CSVs (zip).

It doesn't change settings. It can press two of the SP PRO's front panel buttons for the Home Assistant
integration (Generator start/stop and Silence alarm, as SP LINK's Quick View front panel does).

A log download writes the SP PRO's download-mode and log-search registers,
as SP LINK does, and waits if someone else (SP LINK, the installer via Select.Live) is downloading.

## Connection
- `select_live`: through Select.Live (slower; the installer's path stays as it is).
- `tcp`: raw SP PRO frames over TCP: the ESPHome SP PRO USB link (`sppro`, port 8899; HA is read-only
  there, log downloads allowed) or any transparent serial-to-network bridge on the SP PRO's serial port.
- `serial`: a serial/USB device on the HA machine (`serial_device`, `serial_baudrate`; the SP PRO's
  serial port runs at 57600).

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
