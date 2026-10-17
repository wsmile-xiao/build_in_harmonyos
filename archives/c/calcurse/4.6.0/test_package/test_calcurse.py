#!/usr/bin/env python3
"""calcurse consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

calcurse is an ncurses terminal UI application; the real UI cannot
run in a headless CI ('Error opening terminal' — environment
limitation, honest; upstream make check suite 71/72 already run in
build()). This script verifies the packaged binary is present,
executable and a valid ELF (R34 degraded check).

Usage: test_calcurse.py <package-folder>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "calcurse")
    if not os.path.isfile(exe):
        raise AssertionError(f"calcurse binary missing: {exe}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"calcurse not executable: {exe}")
    with open(exe, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"calcurse is not an ELF binary: {exe}")
    print(f"OK: calcurse binary present and executable ({exe})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
