#!/usr/bin/env python3
"""Verify all runtime assets and the license survive Conan packaging."""
import os
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_assets.py <package-folder>")

    package = sys.argv[1]
    assets = os.path.join(package, "share", "jgrowl")
    required = (
        "jquery.jgrowl.js",
        "jquery.jgrowl.min.js",
        "jquery.jgrowl.css",
        "jquery.jgrowl.min.css",
        "jquery.jgrowl.map",
    )
    for filename in required:
        path = os.path.join(assets, filename)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise AssertionError(f"missing or empty runtime asset: {path}")
        print(f"[ok] {filename} ({os.path.getsize(path)} bytes)")

    license_path = os.path.join(package, "licenses", "LICENSE")
    if not os.path.isfile(license_path) or os.path.getsize(license_path) == 0:
        raise AssertionError(f"missing or empty license: {license_path}")
    print("[ok] MIT license")


if __name__ == "__main__":
    main()
