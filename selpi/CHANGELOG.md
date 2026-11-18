# Changelog

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
