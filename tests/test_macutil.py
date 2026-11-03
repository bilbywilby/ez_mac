import pytest

from ez_address.macutil import (
    MacError,
    classify,
    is_locally_administered,
    is_multicast,
    normalize_mac,
    random_laa,
    set_mac_commands,
)


def test_normalize_mac():
    assert normalize_mac("02-3F-8C-1D-44-A7") == "02:3f:8c:1d:44:a7"


def test_random_laa_is_local_unicast():
    mac = random_laa(prefix="02:3f")
    assert is_locally_administered(mac)
    assert not is_multicast(mac)
    assert mac.startswith("02:3f:")


def test_universal_prefix_is_converted_to_local():
    assert random_laa(prefix="00").startswith("02:")


def test_multicast_prefix_is_rejected():
    with pytest.raises(MacError):
        random_laa(prefix="01")


def test_classify():
    info = classify("02:3f:8c:1d:44:a7")
    assert info.locally_administered
    assert not info.multicast
    assert info.kind == "unicast-local"


def test_commands_are_only_returned():
    commands = set_mac_commands("wlan0", "02:3f:8c:1d:44:a7")
    assert commands[:3] == [
        "ip link set dev wlan0 down",
        "ip link set dev wlan0 address 02:3f:8c:1d:44:a7",
        "ip link set dev wlan0 up",
    ]
