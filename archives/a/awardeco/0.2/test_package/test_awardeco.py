#!/usr/bin/env python3
"""awardeco consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

awardeco decompiles BIOS flash firmware; running it needs an input
BIOS flash file (no sample ships upstream — environment limitation,
honest). This script verifies the packaged binary is present,
executable and a valid ELF (R34 degraded check).

Usage: test_awardeco.py <package-folder>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "awardeco")
    if not os.path.isfile(exe):
        raise AssertionError(f"awardeco binary missing: {exe}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"awardeco not executable: {exe}")
    with open(exe, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"awardeco is not an ELF binary: {exe}")
    print(f"OK: awardeco binary present and executable ({exe})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
