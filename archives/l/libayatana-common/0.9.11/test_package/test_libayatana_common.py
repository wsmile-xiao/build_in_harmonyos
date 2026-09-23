#!/usr/bin/env python3
"""Conan test_package for libayatana-common — R34 real artifact verification.

libayatana-common ships lib/libayatana-common.so (Ayatana indicators common
infrastructure). Verifiable artifacts:
- lib/libayatana-common.so — valid aarch64 ELF shared object (ET_DYN);
- include/ayatana-common.h — the public header (find any include/*.h).
ELF type is checked via magic bytes (no external `file`/`readelf` in the OHOS
sandbox).
"""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"


def _is_elf_shared_object(path):
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    with open(path, "rb") as f:
        f.seek(16)
        raw = f.read(2)
    if len(raw) < 2:
        return False
    e_type = struct.unpack("<H", raw)[0]
    return e_type == 3  # ET_DYN


def _find_header(pkg):
    """Find any public header under <pkg>/include/."""
    inc = os.path.join(pkg, "include")
    if not os.path.isdir(inc):
        return None
    for root, _dirs, files in os.walk(inc):
        for f in sorted(files):
            if f.endswith(".h"):
                return os.path.join(root, f)
    return None


def main():
    pkg = sys.argv[1]
    # 1) libayatana-common shared object present + valid ELF
    so = os.path.join(pkg, "lib", "libayatana-common.so")
    if not os.path.isfile(so):
        print(f"FAIL: libayatana-common.so not found: {so}", file=sys.stderr)
        return 1
    if not _is_elf_shared_object(so):
        print(f"FAIL: {so} is not an ELF shared object", file=sys.stderr)
        return 1
    # 2) public header present
    hdr = _find_header(pkg)
    if not hdr:
        print("FAIL: no public header under include/", file=sys.stderr)
        return 1

    print(f"OK: libayatana-common.so present + ELF shared object, header {hdr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
