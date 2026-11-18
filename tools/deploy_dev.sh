#!/bin/sh
# Development: copy the integration to a Home Assistant over ssh (normal installs use Marketplace).
set -e
cd "$(dirname "$0")/.."
HA=${HA:?set HA=user@your-home-assistant (ssh with sudo), e.g. HA=hassio@homeassistant.local}
tar -c --owner=0 --group=0 --exclude=__pycache__ custom_components/selpi |
  ssh "$HA" "sudo tar -x --no-same-owner -C /config && sudo find /config/custom_components/selpi -maxdepth 1"
echo "restart Home Assistant to load it"
