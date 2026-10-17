#!/usr/bin/env python3
"""test_importlib_metadata.py — consumer test source for
importlib-metadata 9.0.0 (L0c).

REAL API check (R34) on the packaged importlib_metadata:
  distribution() + version + entry_points() — read the metadata of the
  packaged importlib-metadata dist-info itself (real API usage).
Usage: test_importlib_metadata.py <site-packages-dir>
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_importlib_metadata.py "
                         "<site-packages-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "importlib_metadata")):
        raise AssertionError(
            f"importlib_metadata package dir missing under {site}")
    sys.path.insert(0, site)

    import importlib_metadata

    # distribution metadata of the packaged lib itself (real API)
    dist = importlib_metadata.distribution("importlib-metadata")
    if dist is None:
        raise AssertionError("distribution('importlib-metadata') returned "
                             "None — dist-info metadata not found")
    version = dist.version
    if version != "9.0.0":
        raise AssertionError(f"distribution version mismatch: {version}")
    # entry points API (real API surface)
    importlib_metadata.entry_points()

    print(f"OK: importlib-metadata 9.0.0 real API ok "
          f"(distribution {version} / entry_points)")


if __name__ == "__main__":
    main()
