#!/usr/bin/env python3
"""Validate packaged luvit resources against the generated asset manifest."""
import json
import os
import sys


def fail(message):
    raise SystemExit(message)


def main(argv):
    if len(argv) != 2:
        fail("usage: check_luvit_resources.py <package_folder>")
    root = argv[1]
    luvit_root = os.path.join(root, "share", "luvit")
    manifest_path = os.path.join(luvit_root, ".luvit-assets.json")
    if not os.path.isfile(manifest_path):
        fail(f"Missing luvit asset manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as handle:
        assets = json.load(handle)
    if not isinstance(assets, list) or not assets:
        fail("luvit asset manifest is not a non-empty list")

    for entry in assets:
        rel_path = entry.get("path")
        expected_size = entry.get("size")
        if not isinstance(rel_path, str) or not rel_path:
            fail("luvit asset manifest entry is missing path")
        if not isinstance(expected_size, int) or expected_size < 0:
            fail(f"luvit asset manifest entry has invalid size for {rel_path!r}")
        full_path = os.path.join(luvit_root, rel_path)
        if not os.path.isfile(full_path):
            fail(f"Missing packaged luvit resource: {rel_path}")
        if os.path.getsize(full_path) != expected_size:
            fail(f"luvit resource size mismatch for {rel_path}")

    paths = {item["path"] for item in assets}
    for required in ("init.lua", "main.lua", "deps/core.lua", "deps/http.lua", "tests/run.lua"):
        if required not in paths:
            fail(f"Required luvit resource missing from manifest: {required}")

    test_files = [item for item in paths if item.startswith("tests/test-") and item.endswith(".lua")]
    if len(test_files) != 84:
        fail(f"Expected 84 upstream tests/test-*.lua files, found {len(test_files)}")

    print(f"luvit package resources are present ({len(assets)} files, {len(test_files)} upstream test files)")


if __name__ == "__main__":
    main(sys.argv)
