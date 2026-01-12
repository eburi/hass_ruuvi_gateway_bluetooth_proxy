"""BLE advertisement parsing utilities."""
from __future__ import annotations

import logging
from typing import Any

from bleak.backends.scanner import AdvertisementData

_LOGGER = logging.getLogger(__name__)

# AD Type constants
AD_TYPE_FLAGS = 0x01
AD_TYPE_INCOMPLETE_16BIT_SERVICE_UUIDS = 0x02
AD_TYPE_COMPLETE_16BIT_SERVICE_UUIDS = 0x03
AD_TYPE_INCOMPLETE_32BIT_SERVICE_UUIDS = 0x04
AD_TYPE_COMPLETE_32BIT_SERVICE_UUIDS = 0x05
AD_TYPE_INCOMPLETE_128BIT_SERVICE_UUIDS = 0x06
AD_TYPE_COMPLETE_128BIT_SERVICE_UUIDS = 0x07
AD_TYPE_SHORTENED_LOCAL_NAME = 0x08
AD_TYPE_COMPLETE_LOCAL_NAME = 0x09
AD_TYPE_TX_POWER = 0x0A
AD_TYPE_SERVICE_DATA_16BIT = 0x16
AD_TYPE_SERVICE_DATA_32BIT = 0x20
AD_TYPE_SERVICE_DATA_128BIT = 0x21
AD_TYPE_MANUFACTURER_DATA = 0xFF


def parse_advertisement_data(data_hex: str) -> AdvertisementData:
    """
    Parse raw BLE advertisement data from hex string.
    
    Format: Each AD structure is [length][type][data...]
    where length = 1 + len(data)
    
    Returns AdvertisementData with parsed fields.
    """
    try:
        data_bytes = bytes.fromhex(data_hex)
    except ValueError as err:
        _LOGGER.debug("Failed to parse hex data '%s': %s", data_hex, err)
        return AdvertisementData(
            local_name=None,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            rssi=0,
            tx_power=None,
            platform_data=(),
        )

    local_name: str | None = None
    manufacturer_data: dict[int, bytes] = {}
    service_data: dict[str, bytes] = {}
    service_uuids: list[str] = []
    tx_power: int | None = None

    i = 0
    while i < len(data_bytes):
        if i >= len(data_bytes):
            break

        length = data_bytes[i]
        if length == 0:
            # Padding or end of data
            break

        if i + length >= len(data_bytes):
            # Incomplete structure
            _LOGGER.debug("Incomplete AD structure at position %d", i)
            break

        ad_type = data_bytes[i + 1]
        ad_data = data_bytes[i + 2 : i + 1 + length]

        try:
            if ad_type == AD_TYPE_COMPLETE_LOCAL_NAME:
                local_name = ad_data.decode("utf-8", errors="ignore")
            elif ad_type == AD_TYPE_SHORTENED_LOCAL_NAME and local_name is None:
                local_name = ad_data.decode("utf-8", errors="ignore")
            elif ad_type == AD_TYPE_MANUFACTURER_DATA:
                if len(ad_data) >= 2:
                    # First 2 bytes are company ID (little-endian)
                    company_id = int.from_bytes(ad_data[:2], byteorder="little")
                    manufacturer_data[company_id] = ad_data[2:]
            elif ad_type == AD_TYPE_SERVICE_DATA_16BIT:
                if len(ad_data) >= 2:
                    # First 2 bytes are UUID (little-endian)
                    uuid_bytes = ad_data[:2]
                    uuid = f"{uuid_bytes[1]:02x}{uuid_bytes[0]:02x}"
                    service_data[f"0000{uuid}-0000-1000-8000-00805f9b34fb"] = ad_data[
                        2:
                    ]
            elif ad_type == AD_TYPE_SERVICE_DATA_128BIT:
                if len(ad_data) >= 16:
                    # First 16 bytes are UUID (little-endian)
                    uuid_bytes = ad_data[:16]
                    uuid = "-".join(
                        [
                            uuid_bytes[12:16][::-1].hex(),
                            uuid_bytes[10:12][::-1].hex(),
                            uuid_bytes[8:10][::-1].hex(),
                            uuid_bytes[6:8][::-1].hex(),
                            uuid_bytes[0:6][::-1].hex(),
                        ]
                    )
                    service_data[uuid] = ad_data[16:]
            elif ad_type in (
                AD_TYPE_INCOMPLETE_16BIT_SERVICE_UUIDS,
                AD_TYPE_COMPLETE_16BIT_SERVICE_UUIDS,
            ):
                # Parse 16-bit UUIDs
                for j in range(0, len(ad_data), 2):
                    if j + 1 < len(ad_data):
                        uuid_bytes = ad_data[j : j + 2]
                        uuid = f"{uuid_bytes[1]:02x}{uuid_bytes[0]:02x}"
                        service_uuids.append(
                            f"0000{uuid}-0000-1000-8000-00805f9b34fb"
                        )
            elif ad_type in (
                AD_TYPE_INCOMPLETE_128BIT_SERVICE_UUIDS,
                AD_TYPE_COMPLETE_128BIT_SERVICE_UUIDS,
            ):
                # Parse 128-bit UUIDs
                for j in range(0, len(ad_data), 16):
                    if j + 15 < len(ad_data):
                        uuid_bytes = ad_data[j : j + 16]
                        uuid = "-".join(
                            [
                                uuid_bytes[12:16][::-1].hex(),
                                uuid_bytes[10:12][::-1].hex(),
                                uuid_bytes[8:10][::-1].hex(),
                                uuid_bytes[6:8][::-1].hex(),
                                uuid_bytes[0:6][::-1].hex(),
                            ]
                        )
                        service_uuids.append(uuid)
            elif ad_type == AD_TYPE_TX_POWER:
                if len(ad_data) >= 1:
                    # Signed 8-bit integer
                    tx_power = int.from_bytes(ad_data[:1], byteorder="little", signed=True)

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Error parsing AD type 0x%02x: %s", ad_type, err)

        i += length + 1

    return AdvertisementData(
        local_name=local_name,
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids,
        rssi=0,  # Will be set by caller
        tx_power=tx_power,
        platform_data=(),
    )
