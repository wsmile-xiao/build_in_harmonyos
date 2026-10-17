#!/usr/bin/env python3
"""Validate the packaged BusyBox-compatible binary keyboard maps."""

import gzip
import platform
import sys
from pathlib import Path


MAGIC = b"bkeymap"
KEYMAP_TABLES = 256
KEYS_PER_TABLE = 128
BYTES_PER_KEY = 2


def fail(message):
    raise SystemExit(message)


def parse_bkeymap(data, path):
    if not data.startswith(MAGIC):
        fail(f"{path}: missing BusyBox bkeymap signature")

    offset = len(MAGIC)
    flags = data[offset : offset + KEYMAP_TABLES]
    if len(flags) != KEYMAP_TABLES:
        fail(f"{path}: truncated keymap table flags")
    if any(flag not in (0, 1) for flag in flags):
        fail(f"{path}: invalid keymap table flag")

    offset += KEYMAP_TABLES
    populated_tables = sum(flags)
    expected_size = (
        offset + populated_tables * KEYS_PER_TABLE * BYTES_PER_KEY
    )
    if len(data) != expected_size:
        fail(
            f"{path}: invalid bkeymap payload length "
            f"({len(data)} bytes, expected {expected_size})"
        )
    if populated_tables == 0:
        fail(f"{path}: no keymap tables were populated")


def main():
    if len(sys.argv) not in (2, 3):
        fail("usage: test_bkeymaps.py <share/bkeymaps> [--ohos]")

    root = Path(sys.argv[1])
    ohos_target = len(sys.argv) == 3 and sys.argv[2] == "--ohos"
    maps = sorted(root.rglob("*.bmap.gz"))
    if not maps:
        fail(f"{root}: package contains no .bmap.gz keymaps")
    if len(maps) < 180:
        fail(f"{root}: expected the complete keymap set, found only {len(maps)} maps")

    us_map = root / "us" / "us.bmap.gz"
    if not us_map.is_file():
        fail(f"{us_map}: canonical US keymap is missing")

    for path in maps:
        try:
            with gzip.open(path, "rb") as stream:
                data = stream.read()
        except (OSError, EOFError) as error:
            fail(f"{path}: gzip validation failed: {error}")
        parse_bkeymap(data, path)

    if ohos_target:
        if platform.system().lower() != "harmonyos":
            fail(
                "OHOS package test is expected to run on HarmonyOS; "
                f"reported system is {platform.system()}"
            )
        if platform.machine().lower() not in ("aarch64", "arm64"):
            fail(
                "OHOS package test is expected to run on AArch64; "
                f"reported machine is {platform.machine()}"
            )

    print(
        f"validated {len(maps)} bkeymaps; "
        f"OHOS AArch64 check={'enabled' if ohos_target else 'not requested'}"
    )


if __name__ == "__main__":
    main()
