#!/usr/bin/env python3
"""Write an atomic, permission-restricted repository handover report."""

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args):
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "handover-report.json",
        help="Report path (default: handover-report.json in the repository)",
    )
    args = parser.parse_args()

    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)

    packages = sorted(
        (
            {"name": dist.metadata.get("Name", ""), "version": dist.version}
            for dist in distributions()
        ),
        key=lambda item: item["name"].lower(),
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "path": str(ROOT),
            "branch": git("branch", "--show-current"),
            "commit": git("rev-parse", "HEAD"),
            "status": git("status", "--short"),
        },
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "installed_packages": packages,
    }

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_path = Path(temp.name)
            json.dump(report, temp, indent=2)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())

        os.chmod(temp_path, 0o600)
        os.replace(temp_path, output)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
