#!/usr/bin/env python3
"""Conan test_package for polkit — R34 real artifact verification.

polkit ships shared libraries (libpolkit-gobject-1.so) and CLI tools
(pkaction/pkcheck/pkexec). The verifiable artifacts here (without a running
D-Bus system bus, which OHOS lacks) are:
- libpolkit-gobject-1.so under <pkg>/lib — valid ELF shared object;
- a CLI (pkaction) under <pkg>/bin — valid ELF executable.
ELF type is checked via magic bytes (no external `file`/`readelf` in the
OHOS sandbox).
"""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"


def _is_elf(path, want_so=False):
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    with open(path, "rb") as f:
        f.seek(16)
        e_type = struct.unpack("<H", f.read(2))[0]
    if want_so:
        return e_type == 3  # ET_DYN (shared object)
    return True


def _find_so(lib_dir, prefix):
    """Find libpolkit-gobject-1.so* under lib_dir (any suffix)."""
    if not os.path.isdir(lib_dir):
        return None
    for name in sorted(os.listdir(lib_dir)):
        if name.startswith(prefix):
            p = os.path.join(lib_dir, name)
            if os.path.isfile(p) and not os.path.islink(p):
                return p
    return None


def main():
    pkg = sys.argv[1]
    # 1) libpolkit-gobject-1 shared object present + valid ELF
    lib_dir = os.path.join(pkg, "lib")
    so = _find_so(lib_dir, "libpolkit-gobject-1.so")
    if not so:
        print(f"FAIL: libpolkit-gobject-1.so not found under {lib_dir}",
              file=sys.stderr)
        return 1
    if not _is_elf(so, want_so=True):
        print(f"FAIL: {so} is not an ELF shared object", file=sys.stderr)
        return 1
    # 2) CLI (pkaction) present + valid ELF executable
    cli = os.path.join(pkg, "bin", "pkaction")
    if not os.path.isfile(cli):
        print(f"FAIL: pkaction not found: {cli}", file=sys.stderr)
        return 1
    if not _is_elf(cli):
        print(f"FAIL: {cli} is not an ELF executable", file=sys.stderr)
        return 1

    print(f"OK: polkit libpolkit-gobject-1.so present + ELF, pkaction present + ELF")
    return 0


if __name__ == "__main__":
    sys.exit(main())
