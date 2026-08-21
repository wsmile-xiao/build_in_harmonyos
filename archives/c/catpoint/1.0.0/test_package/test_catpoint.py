#!/usr/bin/env python3
"""catpoint consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

catpoint is an ncurses terminal slideshow tool; the real UI cannot
run in a headless CI ('Error opening terminal' — environment
limitation, honest). This script verifies the packaged binary is
present, executable and a valid ELF (R34 degraded check).

Usage: test_catpoint.py <package-folder>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "catpoint")
    if not os.path.isfile(exe):
        raise AssertionError(f"catpoint binary missing: {exe}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"catpoint not executable: {exe}")
    with open(exe, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"catpoint is not an ELF binary: {exe}")
    print(f"OK: catpoint binary present and executable ({exe})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
