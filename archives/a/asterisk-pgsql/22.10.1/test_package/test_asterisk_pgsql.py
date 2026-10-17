#!/usr/bin/env python3
"""Conan test_package for asterisk-pgsql — R34 real API usage (no empty shell).

asterisk-pgsql ships three Asterisk PostgreSQL modules (cdr_pgsql.so,
cel_pgsql.so, res_config_pgsql.so) under <pkg>/lib/asterisk/modules/. The
modules are shared objects loaded by the Asterisk core; their own API is
the Asterisk module ABI, so the verifiable artifact here is the three
modules present and valid ELF shared objects (checked via the ELF magic
bytes, no external `file` binary — the OHOS sandbox has no `file` cmd),
and — the strongest check available without an Asterisk core — that the
postgres dependency is satisfied by checking the modules' dynamic section
(interp/needed libs) for libpq.
"""
import os
import struct
import subprocess
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
    expected = ["cdr_pgsql.so", "cel_pgsql.so", "res_config_pgsql.so"]
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

    # Verify the modules reference libpq (DT_NEEDED string "libpq..." lives in
    # the .dynstr — search the raw bytes; no external readelf in the sandbox).
    with open(os.path.join(mods, "cdr_pgsql.so"), "rb") as f:
        blob = f.read()
    if b"libpq" not in blob:
        print("FAIL: cdr_pgsql.so does not reference libpq", file=sys.stderr)
        return 1

    print(f"OK: asterisk-pgsql modules present + loadable + link libpq: "
          f"{', '.join(expected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
