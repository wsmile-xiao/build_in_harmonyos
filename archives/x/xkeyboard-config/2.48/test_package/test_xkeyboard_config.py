#!/usr/bin/env python3
"""Semantic consumer checks for the installed XKB data package."""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_xkeyboard_config.py PACKAGE_ROOT INVENTORY", file=sys.stderr)
        return 2

    package_root = Path(sys.argv[1]).resolve()
    inventory_path = Path(sys.argv[2]).resolve()
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assertions = 0

    expected_hash = "b77041324f0109f77161ee43743fe04baa485866af8460d31e476ad3f7648fd5"
    if inventory.get("source_archive_sha256") != expected_hash:
        raise AssertionError("inventory is not bound to the official source archive")
    assertions += 1

    root = package_root / "share" / "xkeyboard-config-2"
    if not root.is_dir():
        raise AssertionError(f"missing XKB root: {root}")
    assertions += 1

    for name, expected in inventory["installed_regular_file_minimums"].items():
        directory = root / name
        files = [
            path
            for path in directory.rglob("*")
            if path.is_file() and not path.is_symlink()
        ]
        if len(files) < expected:
            raise AssertionError(f"{name} source closure is short: {len(files)} < {expected}")
        assertions += 1

    for name in inventory["generated_rules"]:
        path = root / "rules" / name
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"generated rule is missing or empty: {path}")
        assertions += 1

    for name in ("base.xml", "base.extras.xml", "evdev.xml", "evdev.extras.xml"):
        path = root / "rules" / name
        tree = ET.parse(path)
        if tree.getroot().tag != "xkbConfigRegistry":
            raise AssertionError(f"unexpected XML root in {path}")
        assertions += 1

    legacy = package_root / "share" / "X11" / "xkb"
    if not legacy.is_symlink():
        raise AssertionError("legacy X11/xkb alias is not a symlink")
    legacy_target = os.readlink(legacy)
    if legacy_target != "/share/xkeyboard-config-2" and legacy.resolve() != root:
        raise AssertionError(
            f"legacy X11/xkb alias has unexpected target: {legacy_target!r}"
        )
    assertions += 1

    pc = package_root / "share" / "pkgconfig" / "xkeyboard-config-2.pc"
    alias = package_root / "share" / "pkgconfig" / "xkeyboard-config.pc"
    content = pc.read_text(encoding="utf-8")
    for line in (
        "prefix=${pcfiledir}/../..",
        "datarootdir=${prefix}/share",
        "datadir=${datarootdir}",
        "xkb_root=${datadir}/xkeyboard-config-2",
        "xkb_base=${datadir}/X11/xkb",
    ):
        if line not in content:
            raise AssertionError(f"relocatable pkg-config field missing: {line}")
        assertions += 1
    if not alias.exists() or alias.resolve() != pc.resolve():
        raise AssertionError("unversioned pkg-config alias is not valid")
    assertions += 1

    license_file = package_root / "licenses" / "COPYING"
    if not license_file.is_file() or license_file.stat().st_size == 0:
        raise AssertionError("COPYING was not packaged")
    assertions += 1

    print(f"XKEYBOARD_CONFIG_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
