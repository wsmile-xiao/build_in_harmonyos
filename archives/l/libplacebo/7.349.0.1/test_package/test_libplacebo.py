#!/usr/bin/env python3
"""libplacebo consumer test (L0c + R34: standalone test source executed
via self.run from conanfile.py test()).

libplacebo video rendering needs GPU/display (absent on OHOS —
environment limitation, honest). Verify packaged library + headers
present and the shared lib is a valid ELF (R34 degraded).

Usage: test_libplacebo.py <package-folder>
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
             if f.startswith("libplacebo.so")]
    if not found:
        raise AssertionError(f"libplacebo.so missing in {libdir}")
    so = os.path.join(libdir, found[0])
    with open(so, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        raise AssertionError(f"{so} is not an ELF shared library")
    incdir = os.path.join(pkg, "include", "libplacebo")
    headers = [f for f in os.listdir(incdir) if f.endswith(".h")]
    if len(headers) < 5:
        raise AssertionError(
            f"libplacebo headers incomplete ({len(headers)} found)")
    print(f"OK: libplacebo present ({found[0]}, {len(headers)} headers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
