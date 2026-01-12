"""Tests for advertisement parser."""
import pytest

from custom_components.ruuvi_gateway_bt_proxy.advertisement_parser import (
    parse_advertisement_data,
)


def test_parse_manufacturer_data():
    """Test parsing manufacturer data."""
    # Apple iBeacon-like format: 0xFF (manufacturer) + company ID + data
    data_hex = "02011A1BFF4C000215UUID16BYTESHEREMAJORMINORTXPOW"
    
    ad_data = parse_advertisement_data(data_hex)
    
    # Should have manufacturer data with Apple company ID (0x004C)
    assert 0x004C in ad_data.manufacturer_data


def test_parse_ruuvi_manufacturer_data():
    """Test parsing Ruuvi manufacturer data."""
    # Ruuvi format: length=0x1B, type=0xFF, company=0x0499 (Ruuvi), format=0x05, data...
    data_hex = "02010611FF990405123AB4567800CDCBC80B0000A430"
    
    ad_data = parse_advertisement_data(data_hex)
    
    # Should have manufacturer data with Ruuvi company ID (0x0499)
    assert 0x0499 in ad_data.manufacturer_data
    # Data should start with format byte 0x05
    assert ad_data.manufacturer_data[0x0499][0] == 0x05


def test_parse_local_name():
    """Test parsing complete local name."""
    # 0x09 = Complete Local Name
    data_hex = "0201060C09527575766920544147"  # "Ruuvi TAG"
    
    ad_data = parse_advertisement_data(data_hex)
    
    assert ad_data.local_name == "Ruuvi TAG"


def test_parse_service_data_16bit():
    """Test parsing 16-bit service data."""
    # 0x16 = Service Data - 16-bit UUID
    data_hex = "0201060716AAFE10EE01"
    
    ad_data = parse_advertisement_data(data_hex)
    
    # UUID 0xFEAA (Eddystone) should be present
    assert "0000feaa-0000-1000-8000-00805f9b34fb" in ad_data.service_data


def test_parse_service_uuids_16bit():
    """Test parsing 16-bit service UUIDs."""
    # 0x03 = Complete 16-bit UUIDs
    data_hex = "020106050316AAFE"
    
    ad_data = parse_advertisement_data(data_hex)
    
    # UUID 0xFEAA should be in service UUIDs
    assert "0000feaa-0000-1000-8000-00805f9b34fb" in ad_data.service_uuids


def test_parse_tx_power():
    """Test parsing TX power."""
    # 0x0A = TX Power Level (signed int8)
    data_hex = "02010603020AFC"  # TX Power = -4 dBm
    
    ad_data = parse_advertisement_data(data_hex)
    
    assert ad_data.tx_power == -4


def test_parse_empty_data():
    """Test parsing empty data."""
    ad_data = parse_advertisement_data("")
    
    assert ad_data.local_name is None
    assert len(ad_data.manufacturer_data) == 0
    assert len(ad_data.service_data) == 0
    assert len(ad_data.service_uuids) == 0


def test_parse_invalid_hex():
    """Test parsing invalid hex string."""
    ad_data = parse_advertisement_data("GGHHII")
    
    # Should return empty advertisement data without crashing
    assert ad_data.local_name is None
    assert len(ad_data.manufacturer_data) == 0


def test_parse_incomplete_structure():
    """Test parsing incomplete AD structure."""
    # Length says 10 bytes but only 5 provided
    data_hex = "0A0106AABBCC"
    
    ad_data = parse_advertisement_data(data_hex)
    
    # Should handle gracefully
    assert ad_data is not None


def test_parse_multiple_structures():
    """Test parsing multiple AD structures."""
    # Flags + Complete Name + Manufacturer Data
    data_hex = "020106" "0809527575766954" "05FF990405"
    
    ad_data = parse_advertisement_data(data_hex)
    
    assert ad_data.local_name == "RuuviT"
    assert 0x0499 in ad_data.manufacturer_data
