#!/usr/bin/env python3
"""Conan test_package for tablib — R34 real API usage (no empty shell).

tablib is pure Python. The verifiable artifact is the tablib package under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged tablib
and actually creates a Dataset + adds rows/headers, then exports to CSV —
proving the package is functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "tablib")):
        print(f"FAIL: tablib package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import tablib

    # R34: build a real Dataset and export to CSV (core format, no extra deps)
    data = tablib.Dataset()
    data.headers = ["name", "age"]
    data.append(["Alice", 30])
    data.append(["Bob", 25])
    csv = data.export("csv")
    if "name,age" not in csv or "Alice,30" not in csv or "Bob,25" not in csv:
        print(f"FAIL: CSV export unexpected:\n{csv}", file=sys.stderr)
        return 1

    print(f"OK: tablib imported from package; CSV export:\n{csv.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
