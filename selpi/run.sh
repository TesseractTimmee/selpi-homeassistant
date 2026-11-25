#!/usr/bin/with-contenv bashio
# Map the add-on options to selpi's SELPI_* environment and start the web UI (ingress).
set -e
CONN="$(bashio::config 'connection')"
if [ "$CONN" = "tcp" ]; then
  export SELPI_CONNECTION_TYPE=TCP
  export SELPI_CONNECTION_TCP_HOSTNAME="$(bashio::config 'tcp_host')"
  export SELPI_CONNECTION_TCP_PORT="$(bashio::config 'tcp_port')"
elif [ "$CONN" = "serial" ]; then
  export SELPI_CONNECTION_TYPE=Serial
  export SELPI_CONNECTION_SERIAL_PORT="$(bashio::config 'serial_device')"
  export SELPI_CONNECTION_SERIAL_BAUDRATE="$(bashio::config 'serial_baudrate')"
else
  export SELPI_CONNECTION_TYPE=SelectLive
  export SELPI_CONNECTION_SELECT_LIVE_USERNAME="$(bashio::config 'select_live_username')"
  export SELPI_CONNECTION_SELECT_LIVE_PASSWORD="$(bashio::config 'select_live_password')"
  export SELPI_CONNECTION_SELECT_LIVE_DEVICE="$(bashio::config 'select_live_device')"
  export SELPI_CONNECTION_SELECT_LIVE_SERVER="$(bashio::config 'select_live_server')"
fi
export SELPI_SPPRO_PASSWORD="$(bashio::config 'sppro_password')"
export SELPI_BACKUP_TIME="$(bashio::config 'backup_time')"
export SELPI_BACKUP_KEEP="$(bashio::config 'backup_keep')"
export SELPI_CLOCK_SYNC="$(bashio::config 'clock_sync')"
export SELPI_CLOCK_MAX_DRIFT="$(bashio::config 'clock_max_drift')"
export SELPI_ALLOW_CONFIG_WRITES="$(bashio::config 'allow_config_writes')"
export SELPI_LOG_LEVEL="$(bashio::config 'log_level')"
export SELPI_DATA_DIR=/data
# Caching (optional; default by connection: Select.Live caches, a direct link reads fresh). Only export when set
# so selpi's own per-connection defaults apply otherwise.
if bashio::config.has_value 'cache_ttl'; then
  export SELPI_CACHE_TTL="$(bashio::config 'cache_ttl')"
fi
if bashio::config.has_value 'stale_grace'; then
  export SELPI_STALE_GRACE="$(bashio::config 'stale_grace')"
fi
# SP LINK proxy (off by default): container port 8899, mapped to a host port in the app's Network settings
if bashio::config.true 'proxy'; then
  export SELPI_PROXY_PORT=8899
  export SELPI_PROXY_ALLOWED="$(bashio::config 'proxy_allowed' | tr '\n' ',')"
  export SELPI_PROXY_WRITE="$(bashio::config 'proxy_write' | tr '\n' ',')"
  export SELPI_PROXY_LOG_DOWNLOADS="$(bashio::config 'proxy_log_downloads')"
fi
# Moving from another install: import its token, id and backups once (from /share/selpi-migrate)
M=/share/selpi-migrate
if [ ! -s /data/install_id ] && [ -s "$M/install_id" ]; then
  cp "$M/install_id" /data/install_id
  [ -s "$M/api_token" ] && cp "$M/api_token" /data/api_token
  [ -d "$M/backups" ] && mkdir -p /data/backups && cp -a "$M/backups/." /data/backups/
  mv "$M" "$M.imported-$(date +%Y%m%d-%H%M%S)"
  bashio::log.info "selpi: imported install id, API token and backups from $M"
fi
# HA API for the selpi integration: a token and an id that survive restarts and updates
[ -s /data/api_token ] || python3 -c "import secrets; print(secrets.token_urlsafe(32))" > /data/api_token
[ -s /data/install_id ] || python3 -c "import uuid; print(uuid.uuid4().hex)" > /data/install_id
export SELPI_API_PORT=8100
export SELPI_API_TOKEN="$(cat /data/api_token)"
export SELPI_INSTALL_ID="$(cat /data/install_id)"
# announce to HA only once the API answers, so the integration's first probe succeeds
announce() {
  for _ in $(seq 1 60); do
    curl -sf -o /dev/null -H "Authorization: Bearer ${SELPI_API_TOKEN}" http://127.0.0.1:8100/api/v1/info && break
    sleep 1
  done
  if bashio::discovery "selpi" "$(bashio::var.json host "$(hostname)" port "^8100" token "${SELPI_API_TOKEN}")" > /dev/null; then
    bashio::log.info "selpi: announced to Home Assistant (integration discovery)"
  else
    bashio::log.warning "selpi: discovery failed; add the integration by hand (host $(hostname), port 8100, token in /data/api_token)"
  fi
}
announce &
bashio::log.info "selpi: ${SELPI_CONNECTION_TYPE}, daily backup ${SELPI_BACKUP_TIME:-off}, clock sync ${SELPI_CLOCK_SYNC}, SP LINK proxy ${SELPI_PROXY_PORT:-off}"
exec python3 -m web.server --port 8099
