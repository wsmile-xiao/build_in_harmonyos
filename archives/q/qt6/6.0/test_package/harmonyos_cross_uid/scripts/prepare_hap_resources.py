#!/usr/bin/env python3
"""Materialize the DevEco app icons from the text-only checked-in asset."""

import base64
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_SOURCE = PROJECT_ROOT / "assets" / "app_icon.png.base64"
ICON_DESTINATIONS = (
    PROJECT_ROOT / "AppScope/resources/base/media/app_icon.png",
    PROJECT_ROOT / "entry/src/main/resources/base/media/app_icon.png",
)


def main() -> None:
    encoded = ICON_SOURCE.read_text(encoding="ascii").strip()
    png = base64.b64decode(encoded, validate=True)
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{ICON_SOURCE} does not contain a PNG image")

    for destination in ICON_DESTINATIONS:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(png)
        print(f"Generated {destination.relative_to(PROJECT_ROOT)} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
