"""Constants for the selpi integration."""

DOMAIN = "selpi"
CONF_TOKEN = "token"
CONF_ADDON_SLUG = "addon_slug"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FAST_SCAN_INTERVAL = "fast_scan_interval"   # faster poll for the live power/voltage/frequency/SoC fields
CONF_GRACE = "grace"               # seconds to keep the last values on a failed poll before entities go unavailable
CONF_ESP_PRESENT = "esp_present"   # the ESPHome sppro component also runs: hide the duplicate SP PRO data sensors
DEFAULT_PORT = 8100
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600
# The fast poll covers only the "fast" fields (the add-on's catalog `fast` flag: the Now power/volt/freq/SoC
# block + the Technical power-flow block). 15 s default is a safe cadence over Select.Live even once the link is
# kept warm; 5 s minimum for a local ESP/serial link. Leave it >= the main interval to effectively disable it.
MIN_FAST_SCAN_INTERVAL = 5
MAX_FAST_SCAN_INTERVAL = 3600
DEFAULT_FAST_SCAN_INTERVAL = 15
MIN_GRACE = 0                      # 0 = go unavailable on the first failed poll (fast 'unknown' on a reliable link)
MAX_GRACE = 3600
DEFAULT_GRACE_SECONDS = 240        # used only when the add-on predates stale_grace in /api/info: ~4 failed polls
                                   # at a 60 s interval, preserving the old resilient default for that case
