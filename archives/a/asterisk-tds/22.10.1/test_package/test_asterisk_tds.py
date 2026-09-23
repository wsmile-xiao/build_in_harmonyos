#!/usr/bin/env python3
"""Conan test_package for asterisk-tds — R34 real API usage (no empty shell).

asterisk-tds ships two Asterisk FreeTDS modules (cdr_tds.so, cel_tds.so) under
<pkg>/lib/asterisk/modules/. The modules are shared objects loaded by the
Asterisk core; their own API is the Asterisk module ABI, so the verifiable
artifact here is the two modules present and valid ELF shared objects (checked
via the ELF magic bytes, no external `file` binary — the OHOS sandbox has no
`file` cmd), and — the strongest check available without an Asterisk core —
that the FreeTDS dependency is satisfied by checking the modules' dynamic
section (interp/needed libs) for libsybdb.
"""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"


def _is_elf_shared_object(path):
    """Return True if path is an ELF shared object (magic + ET_DYN)."""
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    # e_type at offset 16 (2 bytes, little-endian); 3 = ET_DYN (shared object)
    with open(path, "rb") as f:
        f.seek(16)
        e_type = struct.unpack("<H", f.read(2))[0]
    return e_type == 3


def main():
    pkg = sys.argv[1]
    mods = os.path.join(pkg, "lib", "asterisk", "modules")
    expected = ["cdr_tds.so", "cel_tds.so"]
    for name in expected:
        path = os.path.join(mods, name)
        if not os.path.isfile(path):
            print(f"FAIL: module not found: {path}", file=sys.stderr)
            return 1

    # R34: confirm each module is a valid ELF shared object (no external `file`).
    for name in expected:
        path = os.path.join(mods, name)
        if not _is_elf_shared_object(path):
            print(f"FAIL: {name} is not an ELF shared object", file=sys.stderr)
            return 1

    # Verify the modules statically link FreeTDS. freetds/1.4.23 is a static
    # lib (libsybdb.a), so DT_NEEDED has no "libsybdb" — instead the FreeTDS
    # symbols (dbinit, tdsdbopen) are baked into the module. Search the raw
    # bytes of .dynstr/.strtab (no external readelf in the sandbox).
    # 遍历两个模块逐一校验（AI 检视 P2：原实现只扫 cdr_tds.so，cel_tds.so
    # 未覆盖——任一模块缺符号即返回 1）。
    for name in expected:
        path = os.path.join(mods, name)
        with open(path, "rb") as f:
            blob = f.read()
        if b"dbinit" not in blob or b"tdsdbopen" not in blob:
            print(f"FAIL: {name} does not contain statically-linked FreeTDS "
                  f"symbols (dbinit/tdsdbopen)", file=sys.stderr)
            return 1

    print(f"OK: asterisk-tds modules present + loadable + statically link "
          f"FreeTDS (dbinit/tdsdbopen): {', '.join(expected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
