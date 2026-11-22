"""Constants for the selpi integration."""

DOMAIN = "selpi"
CONF_TOKEN = "token"
CONF_ADDON_SLUG = "addon_slug"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ESP_PRESENT = "esp_present"   # the ESPHome sppro component also runs: hide the duplicate SP PRO data sensors
DEFAULT_PORT = 8100
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600
