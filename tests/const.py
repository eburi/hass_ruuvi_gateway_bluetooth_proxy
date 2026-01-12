"""Constants for tests."""

# Mock MQTT message
MOCK_MQTT_TOPIC = "ruuvi/C1:05:28:BF:A7:E7/6B:EF:59:3C:53:D9"

MOCK_MQTT_PAYLOAD = {
    "gw_mac": "C1:05:28:BF:A7:E7",
    "rssi": -49,
    "aoa": [],
    "gwts": 1768151705,
    "ts": 1768151705,
    "data": "02010611FF990405123AB4567800CDCBC80B0000A430",
    "coords": "",
}

# Ruuvi manufacturer data example (format 5)
RUUVI_DATA_FORMAT_5 = "02010611FF990405123AB4567800CDCBC80B0000A430"
