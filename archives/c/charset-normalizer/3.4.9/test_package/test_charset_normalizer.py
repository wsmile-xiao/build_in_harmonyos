#!/usr/bin/env python3
"""Conan test_package for charset-normalizer — R34 real API usage (no empty shell).

charset-normalizer is pure Python. The verifiable artifact is the
charset_normalizer package under <pkg>/lib/python3.12/site-packages/. This
test imports the packaged module and actually detects the encoding of a
byte string — proving the package is functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "charset_normalizer")):
        print(f"FAIL: charset_normalizer package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    from charset_normalizer import from_bytes

    # R34: detect encoding of a UTF-8 byte string
    raw = "你好，世界".encode("utf-8")
    best = from_bytes(raw).best()
    if best is None or best.encoding not in ("utf_8", "utf-8"):
        print(f"FAIL: from_bytes best={best!r}, expected utf_8",
              file=sys.stderr)
        return 1

    print(f"OK: charset_normalizer imported from package; "
          f"detected={best.encoding}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
