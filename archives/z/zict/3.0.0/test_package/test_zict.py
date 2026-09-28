#!/usr/bin/env python3
"""Exercise zict's public API from a Conan consumer environment."""
import os
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_zict.py <site-packages-dir>")
    site_packages = sys.argv[1]
    if not os.path.isdir(os.path.join(site_packages, "zict")):
        raise AssertionError(f"zict package directory missing: {site_packages}")
    sys.path.insert(0, site_packages)

    import zict

    if zict.__version__ != "3.0.0":
        raise AssertionError(f"unexpected zict version: {zict.__version__}")

    backing = {}
    cache = zict.LRU(2, backing)
    cache["a"] = 1
    cache["b"] = 2
    if cache["a"] != 1 or cache["b"] != 2:
        raise AssertionError("LRU lookup did not return stored values")
    cache["c"] = 3
    if len(cache) != 2 or "a" in backing or backing != {"b": 2, "c": 3}:
        raise AssertionError(f"LRU eviction result was incorrect: {backing!r}")
    if "zict" not in zict.__file__:
        raise AssertionError(f"import did not resolve from packaged site: {zict.__file__}")

    print("OK: zict 3.0.0 import and LRU consumer behavior")


if __name__ == "__main__":
    main()
