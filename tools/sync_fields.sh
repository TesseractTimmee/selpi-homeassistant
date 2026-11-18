#!/bin/sh
# Copy selpi's field tables into the ESPHome component, from the selpi fork at the version the app pins
# (SELPI_REF in selpi/Dockerfile), so the ESP and the app read the same fields.
#   tools/sync_fields.sh [ref]     (default: the app's SELPI_REF)
set -e
cd "$(dirname "$0")/.."
REF=${1:-$(sed -n 's/^ARG SELPI_REF=//p' selpi/Dockerfile)}
URL=https://raw.githubusercontent.com/TesseractTimmee/selpi/$REF/sppro
for f in live_fields.json splink_tables.json default_fields.json; do
  curl -fsSL "$URL/$f" -o esphome/components/sppro/$f
done
echo "esphome/components/sppro: field tables from selpi $REF"
git status --short esphome/components/sppro
