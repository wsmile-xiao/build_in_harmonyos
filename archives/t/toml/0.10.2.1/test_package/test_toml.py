#!/usr/bin/env python3
"""test_toml.py — consumer test source for toml 0.10.2 (L0c).

REAL API check (R34) on the packaged toml:
  1) import toml
  2) toml.loads — parse a TOML doc (core decode API)
  3) toml.dumps — serialize a dict back to TOML (core encode API)
Usage: test_toml.py <site-packages-dir>
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_toml.py <site-packages-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "toml")):
        raise AssertionError(f"toml package dir missing under {site}")
    sys.path.insert(0, site)

    import toml

    # toml.loads: decode a TOML doc
    doc = toml.loads('title = "example"\n[owner]\nname = "Tom"\nage = 42\n')
    if doc["title"] != "example":
        raise AssertionError(f"toml.loads title mismatch: {doc['title']}")
    if doc["owner"]["name"] != "Tom" or doc["owner"]["age"] != 42:
        raise AssertionError(f"toml.loads nested mismatch: {doc['owner']}")

    # toml.dumps: encode back (round-trip)
    dumped = toml.dumps({"title": "example", "owner": {"name": "Tom"}})
    if "title" not in dumped or "Tom" not in dumped:
        raise AssertionError(f"toml.dumps round-trip mismatch: {dumped}")

    print("OK: toml 0.10.2 real API ok (loads/dumps)")


if __name__ == "__main__":
    main()
