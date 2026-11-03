#!/usr/bin/env python3
"""Generate a locally administered MAC profile; does not apply it."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ez_address.macutil import classify, random_laa, set_mac_commands, MacError


IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
PREFIX_RE = re.compile(r"^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){0,2}$")


def validate_interface(interface: str) -> str:
    if not IFACE_RE.fullmatch(interface):
        raise ValueError(
            "Invalid interface name; use 1–15 letters, digits, '.', '_', ':', or '-'"
        )
    return interface


def validate_prefix(prefix: str | None) -> str | None:
    if prefix is None:
        return None
    if not PREFIX_RE.fullmatch(prefix):
        raise ValueError("Prefix must contain 1–3 colon-separated hex octets")

    first_octet = int(prefix[:2], 16)
    if first_octet & 1:
        raise ValueError("Prefix must be unicast (multicast bit must be clear)")
    if not first_octet & 2:
        raise ValueError("Prefix must be locally administered (LAA bit must be set)")
    return prefix


def build_device_profile(interface: str, prefix: str | None = None) -> dict:
    interface = validate_interface(interface)
    prefix = validate_prefix(prefix)

    mac = random_laa(prefix=prefix)
    info = classify(mac)

    if not info.locally_administered:
        raise ValueError("MAC utility returned an address that is not locally administered")

    return {
        "interface": interface,
        "mac_address": info.mac,
        "oui": info.oui,
        "is_laa": info.locally_administered,
        "kind": info.kind,
        "provisioning_commands": set_mac_commands(interface, info.mac),
    }


def write_private_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            os.fchmod(temp_file.fileno(), 0o600)
            temp_file.write(content)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an authorized device MAC provisioning profile."
    )
    parser.add_argument(
        "--iface",
        default="wlan0",
        help="Target interface name (default: wlan0; use the actual interface name)",
    )
    parser.add_argument(
        "--prefix",
        help="Optional 1–3 octet locally administered unicast prefix, e.g. 02:3f",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this path; omit it to print JSON to stdout",
    )
    args = parser.parse_args()

    try:
        profile = build_device_profile(args.iface, args.prefix)
        output = json.dumps(profile, indent=2) + "\n"

        if args.output:
            write_private_atomic(args.output, output)
            print(f"Profile saved to {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(output)

    except (MacError, OSError, ValueError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
