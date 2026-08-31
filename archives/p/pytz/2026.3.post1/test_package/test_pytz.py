#!/usr/bin/env python3
"""Conan test_package for pytz — R34 real API usage (no empty shell).

pytz is pure Python. The verifiable artifact is the pytz package under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged pytz,
fetches a real timezone via timezone() and checks utcoffset — proving the
package AND its zoneinfo data are functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "pytz")):
        print(f"FAIL: pytz package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import datetime

    import pytz

    # R34: fetch a real timezone and check utcoffset (exercises zoneinfo data).
    # NOTE: pytz's utcoffset() requires a datetime arg — utcoffset(None) is None.
    tz = pytz.timezone("Asia/Shanghai")
    offset = tz.utcoffset(datetime.datetime(2026, 1, 1))
    if offset is None:
        print("FAIL: Asia/Shanghai utcoffset is None", file=sys.stderr)
        return 1
    hours = offset.total_seconds() / 3600
    if int(hours) != 8:  # UTC+8
        print(f"FAIL: Asia/Shanghai utcoffset = {offset} (expected +8h)",
              file=sys.stderr)
        return 1

    print(f"OK: pytz imported from package; Asia/Shanghai utcoffset = "
          f"{offset} ({hours}h)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
