"""Constants for the selpi integration."""

DOMAIN = "selpi"
CONF_TOKEN = "token"
CONF_ADDON_SLUG = "addon_slug"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GRACE = "grace"               # seconds to keep the last values on a failed poll before entities go unavailable
CONF_ESP_PRESENT = "esp_present"   # the ESPHome sppro component also runs: hide the duplicate SP PRO data sensors
DEFAULT_PORT = 8100
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600
MIN_GRACE = 0                      # 0 = go unavailable on the first failed poll (fast 'unknown' on a reliable link)
MAX_GRACE = 3600
DEFAULT_GRACE_SECONDS = 240        # used only when the add-on predates stale_grace in /api/info: ~4 failed polls
                                   # at a 60 s interval, preserving the old resilient default for that case
