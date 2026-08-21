#!/usr/bin/env python3
"""bacula-pgsql consumer test (L0c: standalone test source executed
via self.run from conanfile.py test()).

libbaccats-postgresql is the PostgreSQL catalog backend; running it
needs a PostgreSQL server (absent on OHOS — environment limitation,
honest). This script verifies the packaged backend library is present
and a valid ELF (R34 degraded check).

Usage: test_bacula.py <package-folder>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    libdir = os.path.join(pkg, "lib")
    found = [f for f in os.listdir(libdir)
             if f.startswith("libbaccats") and f.endswith(".so")]
    if not found:
        raise AssertionError(f"libbaccats missing in {libdir}")
    so = os.path.join(libdir, found[0])
    with open(so, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"{so} is not an ELF shared library")
    print(f"OK: bacula-pgsql backend present ({found[0]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
