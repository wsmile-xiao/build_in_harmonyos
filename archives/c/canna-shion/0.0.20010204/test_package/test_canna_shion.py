#!/usr/bin/env python3
"""canna-shion 0.0.20010204 consumer test — data package verification.

Checks the installed data package: the 6 .ctd Canna support dictionaries
exist, are non-empty and valid EUC-JP text, and
lib/pkgconfig/canna-shion.pc exists (the L1e destructible artifact).
Exits non-zero on any failure.
"""
import os
import sys

DICTIONARIES = ("basho.ctd", "kaom.ctd", "keisan.ctd",
                "pub.ctd", "scien.ctd", "sup.ctd")


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    for ctd in DICTIONARIES:
        path = os.path.join(pkg_root, "share", "canna-shion", ctd)
        if not os.path.isfile(path):
            print("[FAIL] %s missing" % path)
            failures += 1
            continue
        if os.path.getsize(path) == 0:
            print("[FAIL] %s empty" % path)
            failures += 1
            continue
        try:
            with open(path, "rb") as f:
                data = f.read()
            data.decode("euc_jp")
            print("[ok] %s (%d bytes, valid EUC-JP)" % (ctd, len(data)))
        except UnicodeDecodeError as e:
            print("[FAIL] %s invalid EUC-JP: %s" % (path, e))
            failures += 1

    pc = os.path.join(pkg_root, "lib", "pkgconfig", "canna-shion.pc")
    if not os.path.isfile(pc):
        print("[FAIL] %s missing (L1e destructible artifact)" % pc)
        failures += 1
    else:
        print("[ok] lib/pkgconfig/canna-shion.pc present")

    if failures:
        print("canna-shion: %d assertion(s) failed" % failures)
        return 1
    print("canna-shion package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
