#!/usr/bin/env python3
"""Conan test_package for certifi — R34 real API usage (no empty shell).

certifi is a Python CA-certificate data package. The verifiable artifact is
the certifi package (with cacert.pem) under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged certifi
and reads the real CA bundle via where() — proving the data is functional,
not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "certifi")):
        print(f"FAIL: certifi package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    import certifi

    # R34: read the real CA bundle (exercises cacert.pem data).
    # NOTE: cacert.pem starts with a comment block (# Issuer: ...) before the
    # first certificate — search the whole file for a PEM cert marker.
    bundle = certifi.where()
    if not os.path.isfile(bundle):
        print(f"FAIL: certifi.where() -> {bundle!r} not a file",
              file=sys.stderr)
        return 1
    with open(bundle, "r", encoding="utf-8") as f:
        content = f.read()
    if "BEGIN CERTIFICATE" not in content:
        print(f"FAIL: bundle {bundle!r} has no cert content "
              f"(len={len(content)})", file=sys.stderr)
        return 1

    print(f"OK: certifi imported from package; where() -> {bundle} "
          f"({len(content)} bytes, BEGIN CERTIFICATE present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
