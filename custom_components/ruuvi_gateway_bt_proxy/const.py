"""Constants for the Ruuvi Gateway Bluetooth Proxy integration."""
from typing import Final

DOMAIN: Final = "ruuvi_gateway_bt_proxy"

# Config flow defaults
DEFAULT_TOPIC_PREFIX: Final = "ruuvi/"
DEFAULT_QOS: Final = 0
DEFAULT_BATCH_WINDOW_MS: Final = 250
DEFAULT_RSSI_MIN: Final = -127

# Config keys
CONF_TOPIC_PREFIX: Final = "mqtt_topic_prefix"
CONF_QOS: Final = "mqtt_qos"
CONF_GATEWAY_WHITELIST: Final = "gateway_whitelist"
CONF_DEVICE_WHITELIST: Final = "device_whitelist"
CONF_RSSI_MIN: Final = "rssi_min"
CONF_BATCH_WINDOW_MS: Final = "batch_window_ms"
CONF_DEBUG_ENTITY: Final = "enable_debug_entity"

# Stats/Diagnostics keys
STAT_PACKETS_RECEIVED: Final = "packets_received"
STAT_PACKETS_FORWARDED: Final = "packets_forwarded"
STAT_PACKETS_DROPPED: Final = "packets_dropped"
STAT_INVALID_TOPIC: Final = "invalid_topic"
STAT_INVALID_JSON: Final = "invalid_json"
STAT_INVALID_HEX: Final = "invalid_hex"
STAT_FILTERED_GATEWAY: Final = "filtered_gateway"
STAT_FILTERED_DEVICE: Final = "filtered_device"
STAT_FILTERED_RSSI: Final = "filtered_rssi"
