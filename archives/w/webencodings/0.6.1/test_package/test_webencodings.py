#!/usr/bin/env python3
"""Conan test_package for webencodings — R34 real API usage (no empty shell).

webencodings is pure Python. The verifiable artifact is the webencodings
package under <pkg>/lib/python3.12/site-packages/. This test imports the
packaged webencodings and actually looks up a WHATWG encoding by name —
proving the package is functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "webencodings")):
        print(f"FAIL: webencodings package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import webencodings

    # R34: lookup a WHATWG encoding by name (exercises labels.py)
    enc = webencodings.lookup("utf-8")
    if enc is None or enc.name != "utf-8":
        print(f"FAIL: webencodings.lookup('utf-8') = {enc!r}",
              file=sys.stderr)
        return 1

    print(f"OK: webencodings imported from package; lookup('utf-8') -> "
          f"{enc.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
