"""MAC address classification, generation, and command formatting."""

import random
import re
from dataclasses import dataclass


class MacError(ValueError):
    """Invalid MAC address, prefix, or interface."""


@dataclass(frozen=True)
class MacInfo:
    mac: str
    oui: str
    locally_administered: bool
    multicast: bool
    kind: str


def normalize_mac(mac: str) -> str:
    if not isinstance(mac, str):
        raise MacError("MAC must be a string")

    value = mac.strip().lower()

    if re.fullmatch(r"[0-9a-f]{4}(?:\.[0-9a-f]{4}){2}", value):
        compact = value.replace(".", "")
    elif re.fullmatch(r"[0-9a-f]{12}", value):
        compact = value
    elif re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", value):
        compact = value.replace(":", "")
    elif re.fullmatch(r"[0-9a-f]{2}(?:-[0-9a-f]{2}){5}", value):
        compact = value.replace("-", "")
    else:
        raise MacError("Invalid MAC address format")

    return ":".join(compact[i:i + 2] for i in range(0, 12, 2))


def is_locally_administered(mac: str) -> bool:
    return bool(int(normalize_mac(mac)[:2], 16) & 0x02)


def is_multicast(mac: str) -> bool:
    return bool(int(normalize_mac(mac)[:2], 16) & 0x01)


def oui_of(mac: str) -> str:
    return ":".join(normalize_mac(mac).split(":")[:3])


def classify(mac: str) -> MacInfo:
    normalized = normalize_mac(mac)
    first = int(normalized[:2], 16)
    local = bool(first & 0x02)
    multicast = bool(first & 0x01)

    if multicast:
        kind = "multicast-local" if local else "multicast-universal"
    else:
        kind = "unicast-local" if local else "unicast-universal"

    return MacInfo(
        mac=normalized,
        oui=oui_of(normalized),
        locally_administered=local,
        multicast=multicast,
        kind=kind,
    )


def random_laa(prefix: str = None, rng=None) -> str:
    source = rng if rng is not None else random.SystemRandom()
    octets = []

    if prefix is not None:
        value = prefix.strip().lower().replace("-", ":")
        if not re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){0,2}", value):
            raise MacError("prefix must be 1–3 colon-separated hex octets")

        octets = [int(part, 16) for part in value.split(":")]
        if octets[0] & 0x01:
            raise MacError("prefix must be unicast; multicast bit is set")

        # Set the locally administered bit.
        octets[0] |= 0x02
    else:
        # Set the LAA bit and clear the multicast bit.
        octets = [(source.randint(0, 255) & 0xFC) | 0x02]

    while len(octets) < 6:
        octets.append(source.randint(0, 255))

    return ":".join(f"{byte:02x}" for byte in octets)


def set_mac_commands(interface: str, mac: str) -> list[str]:
    if not isinstance(interface, str) or not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,15}", interface
    ):
        raise MacError("Invalid interface name")

    normalized = normalize_mac(mac)
    return [
        f"ip link set dev {interface} down",
        f"ip link set dev {interface} address {normalized}",
        f"ip link set dev {interface} up",
        f"ip link show {interface}",
    ]
