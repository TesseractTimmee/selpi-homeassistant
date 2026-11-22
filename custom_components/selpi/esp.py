"""Whether the ESPHome sppro component is the SP PRO link — read straight from the add-on's connection type
(its TCP connection is the ESPHome sppro proxy), rather than guessing from ESP sensor names."""
from __future__ import annotations

from typing import Any

from .const import CONF_ESP_PRESENT


def esp_detected(info: dict[str, Any]) -> bool:
    """True when the add-on reaches the SP PRO through the ESP (connection type TCP = the ESPHome sppro proxy)."""
    return (info or {}).get("connection") == "TCP"


def esp_active(entry: Any, info: dict[str, Any]) -> bool:
    """The user's explicit "ESP present" choice if set, otherwise auto-detected from the connection type."""
    chosen = entry.options.get(CONF_ESP_PRESENT)
    return bool(chosen) if chosen is not None else esp_detected(info)
