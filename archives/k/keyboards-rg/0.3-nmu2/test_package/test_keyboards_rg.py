#!/usr/bin/env python3
"""Semantic consumer checks for the installed keyboards-rg data package."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_path(package_root: Path, relative: str) -> Path:
    parts = relative.split("/")
    if not relative or relative.startswith("/") or ".." in parts:
        raise AssertionError(f"unsafe package-relative path: {relative!r}")
    return package_root.joinpath(*parts)


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: test_keyboards_rg.py PACKAGE_ROOT INVENTORY TARGET_OS",
            file=sys.stderr,
        )
        return 2

    package_root = Path(sys.argv[1]).resolve()
    inventory_path = Path(sys.argv[2]).resolve()
    target_os = sys.argv[3]
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assertions = 0

    if not package_root.is_dir():
        raise AssertionError(f"package root is not a directory: {package_root}")
    assertions += 1

    expected_archive_sha256 = (
        "D3139512D68C2A93DB71315F3D1ECEB431DA237C47F4A723F87F9BB62D8D3DF4"
    )
    if inventory.get("source_archive_sha256") != expected_archive_sha256:
        raise AssertionError("inventory is not bound to the official source archive")
    assertions += 1

    for relative, expected_hash in inventory["installed_files"].items():
        path = package_path(package_root, relative)
        if not path.is_file() or path.stat().st_size == 0:
            raise AssertionError(f"installed artifact is missing or empty: {path}")
        assertions += 1
        if sha256(path) != expected_hash:
            raise AssertionError(f"installed artifact hash mismatch: {relative}")
        assertions += 1
        content = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in content for marker in ("/usr/", "/etc/", "C:\\Users\\")):
            raise AssertionError(f"installed artifact contains an absolute host path: {relative}")
        assertions += 1

    if (package_root / "oldfiles").exists():
        raise AssertionError("obsolete oldfiles payload was installed")
    assertions += 1

    for relative in inventory["xkb_layouts"]:
        content = package_path(package_root, relative).read_text(
            encoding="utf-8", errors="replace"
        )
        if "xkb_symbols" not in content:
            raise AssertionError(f"XKB symbols declaration missing: {relative}")
        assertions += 1

    for relative in inventory["console_maps"]:
        content = package_path(package_root, relative).read_text(
            encoding="utf-8", errors="replace"
        )
        if "keymaps " not in content:
            raise AssertionError(f"console keymap header missing: {relative}")
        assertions += 1

    if target_os == "OHOS":
        for relative in inventory["script_paths"]:
            script = package_path(package_root, relative)
            completed = subprocess.run(
                ["sh", "-n", str(script)],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise AssertionError(
                    f"OHOS shell syntax check failed for {relative}: "
                    f"{completed.stderr.strip()}"
                )
            assertions += 1
        print("KEYBOARDS_RG_OHOS_SHELL=PASS scripts=3")

    print(f"KEYBOARDS_RG_CONSUMER=PASS assertions={assertions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
