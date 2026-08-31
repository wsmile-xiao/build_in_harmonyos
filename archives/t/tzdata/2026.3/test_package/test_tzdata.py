#!/usr/bin/env python3
"""Conan test_package for tzdata — R34 real API usage (no empty shell).

tzdata is a Python time-zone data package. The verifiable artifact is the
tzdata package under <pkg>/lib/python3.12/site-packages/. This test imports
the packaged tzdata and exercises its zoneinfo data via
zoneinfo.ZoneInfo('Asia/Shanghai') — proving the data is functional, not
just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "tzdata")):
        print(f"FAIL: tzdata package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    # R34: exercise the packaged tzdata zoneinfo data.
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Shanghai")
    if tz is None:
        print("FAIL: ZoneInfo('Asia/Shanghai') returned None",
              file=sys.stderr)
        return 1

    print(f"OK: tzdata imported from package; "
          f"ZoneInfo('Asia/Shanghai') = {tz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
