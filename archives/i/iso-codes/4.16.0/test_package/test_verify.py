#!/usr/bin/env python3
"""Verify iso-codes data files are correctly installed.

Checks:
  1. All 8 ISO standard JSON files exist and are valid JSON
  2. pkg-config file exists with correct version
  3. At least one .mo translation file exists
"""
import json
import os
import sys


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_ROOT", "")
    if not pkg_root:
        print("ERROR: PACKAGE_ROOT not set", file=sys.stderr)
        return 1

    share_dir = os.path.join(pkg_root, "share")
    json_dir = os.path.join(share_dir, "iso-codes", "json")
    pc_path = os.path.join(share_dir, "pkgconfig", "iso-codes.pc")
    locale_dir = os.path.join(share_dir, "locale")

    errors = 0

    # 1. Check JSON data files
    expected = [
        "iso_639-2.json", "iso_639-3.json", "iso_639-5.json",
        "iso_3166-1.json", "iso_3166-2.json", "iso_3166-3.json",
        "iso_4217.json", "iso_15924.json",
    ]
    for f in expected:
        path = os.path.join(json_dir, f)
        if not os.path.exists(path):
            print(f"FAIL: Missing JSON file: {f}")
            errors += 1
            continue
        with open(path) as fh:
            try:
                data = json.load(fh)
                if not data:
                    print(f"FAIL: Empty JSON data in {f}")
                    errors += 1
                else:
                    print(f"OK: {f} ({len(data)} entries)")
            except json.JSONDecodeError as e:
                print(f"FAIL: Invalid JSON in {f}: {e}")
                errors += 1

    # 2. Check pkg-config file
    if not os.path.exists(pc_path):
        print("FAIL: Missing iso-codes.pc")
        errors += 1
    else:
        with open(pc_path) as fh:
            content = fh.read()
            if "4.16.0" not in content:
                print("FAIL: Version not found in pkg-config file")
                errors += 1
            elif "iso_639-2" not in content:
                print("FAIL: Domains not found in pkg-config file")
                errors += 1
            else:
                print("OK: iso-codes.pc verified")

    # 3. Check at least one .mo file exists
    mo_count = 0
    if os.path.isdir(locale_dir):
        for root, dirs, files in os.walk(locale_dir):
            for f in files:
                if f.endswith(".mo"):
                    mo_count += 1
    if mo_count == 0:
        print("FAIL: No .mo translation files found")
        errors += 1
    else:
        print(f"OK: {mo_count} .mo translation files found")

    if errors > 0:
        print(f"\nRESULT: FAILED ({errors} errors)")
        return 1
    else:
        print("\nRESULT: PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
