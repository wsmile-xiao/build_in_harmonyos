#!/usr/bin/env python3
"""Conan test_package for systemd — R34 real artifact verification.

systemd ships the libsystemd client library (libsystemd.so) plus public headers
(sd-bus.h etc.). The daemons need a running systemd environment (OHOS lacks),
so verification here combines:
- lib/libsystemd.so — valid aarch64 ELF shared object (ET_DYN), with
  EI_CLASS/EI_DATA/e_machine sanity checks;
- include/systemd/sd-bus.h — the public client API header;
- **static .dynsym symbol check** of real libsystemd exports (sd_bus_new,
  sd_bus_default, sd_bus_close) — verifies the shared library actually exports
  its client API (R34: catches missing-symbol / unlinkable regressions).

Symbol presence is checked by parsing the ELF .dynsym/.dynstr section directly
(no dlopen/ctypes): OHOS refuses to load unsigned .so at runtime (dlopen →
"Permission denied", E318), and signing in package() depends on the CI toolchain
having binary-sign-tool. Static .dynsym parsing is load-independent and
deterministic.
"""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"

# ELF64 section header types
SHT_STRTAB = 3
SHT_DYNSYM = 11
# ELF64 symbol binding (st_info >> 4); exported globals are GLOBAL (1) / WEAK (2)
STB_GLOBAL = 1
STB_WEAK = 2


def _is_elf_shared_object(path):
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    # EI_CLASS: 1=32-bit, 2=64-bit (aarch64 → 2)
    if ident[4] != 2:
        return False
    # EI_DATA: 1=LE (aarch64 → little-endian)
    if ident[5] != 1:
        return False
    with open(path, "rb") as f:
        f.seek(16)
        raw = f.read(2)
    if len(raw) < 2:
        return False
    e_type = struct.unpack("<H", raw)[0]
    if e_type != 3:  # ET_DYN
        return False
    # e_machine: 0xB7 (183) = EM_AARCH64 (at offset 18, 2 bytes LE)
    with open(path, "rb") as f:
        f.seek(18)
        machine = struct.unpack("<H", f.read(2))[0]
    return machine == 183


def _read_sections(path):
    """Read ELF64 section headers; return {name: (sh_offset, sh_size, sh_link)}."""
    with open(path, "rb") as f:
        f.seek(0x28)  # e_shoff
        shoff = struct.unpack("<Q", f.read(8))[0]
        f.seek(0x3A)  # e_shentsize
        shentsize = struct.unpack("<H", f.read(2))[0]
        f.seek(0x3C)  # e_shnum
        shnum = struct.unpack("<H", f.read(2))[0]
        f.seek(0x3E)  # e_shstrndx
        shstrndx = struct.unpack("<H", f.read(2))[0]

        # Read the string table section header to map names
        f.seek(shoff + shstrndx * shentsize)
        sh = f.read(shentsize)
        shstr_offset = struct.unpack("<Q", sh[24:32])[0]
        shstr_size = struct.unpack("<Q", sh[32:40])[0]
        f.seek(shstr_offset)
        shstr = f.read(shstr_size)

        sections = {}
        for i in range(shnum):
            f.seek(shoff + i * shentsize)
            sh = f.read(shentsize)
            name_off = struct.unpack("<I", sh[0:4])[0]
            sh_type = struct.unpack("<I", sh[4:8])[0]
            sh_offset = struct.unpack("<Q", sh[24:32])[0]
            sh_size = struct.unpack("<Q", sh[32:40])[0]
            sh_link = struct.unpack("<I", sh[40:44])[0]
            name = shstr[name_off:shstr.find(b"\0", name_off)].decode("utf-8", "replace")
            sections[name] = (sh_type, sh_offset, sh_size, sh_link)
        return sections


def _dynsym_symbols(path, dynsym_name=".dynsym", dynstr_name=".dynstr"):
    """Parse .dynsym/.dynstr and return the set of exported symbol names."""
    sections = _read_sections(path)
    if dynsym_name not in sections or dynstr_name not in sections:
        return set()
    dynsym_type, dynsym_off, dynsym_size, dynstr_link = sections[dynsym_name]
    dynstr_type, dynstr_off, dynstr_size, _ = sections[dynstr_name]
    if dynsym_type != SHT_DYNSYM or dynstr_type != SHT_STRTAB:
        return set()

    exported = set()
    with open(path, "rb") as f:
        f.seek(dynstr_off)
        dynstr = f.read(dynstr_size)
        f.seek(dynsym_off)
        data = f.read(dynsym_size)
    # ELF64 sym: st_name(4) st_info(1) st_other(1) st_shndx(2) st_value(8) st_size(8)
    sym_size = 24
    for i in range(0, len(data) - sym_size + 1, sym_size):
        st_name = struct.unpack("<I", data[i:i+4])[0]
        st_info = data[i+4]
        bind = st_info >> 4
        st_shndx = struct.unpack("<H", data[i+8:i+10])[0]
        if st_shndx == 0:  # SHN_UNDEF — undefined reference, skip
            continue
        if bind not in (STB_GLOBAL, STB_WEAK):
            continue
        end = dynstr.find(b"\0", st_name)
        if end == -1:
            continue
        exported.add(dynstr[st_name:end].decode("utf-8", "replace"))
    return exported


def _check_symbols(so, symbols):
    """Check exported symbols exist in .dynsym; return (ok, missing)."""
    try:
        exported = _dynsym_symbols(so)
    except (OSError, struct.error) as e:
        return False, f"dynsym parse failed: {e}"
    missing = [s for s in symbols if s not in exported]
    return (not missing), missing


def main():
    pkg = sys.argv[1]
    # 1) libsystemd shared object present + valid aarch64 ELF (ET_DYN,
    #    EI_CLASS=64-bit, EI_DATA=LE, e_machine=EM_AARCH64)
    so = os.path.join(pkg, "lib", "libsystemd.so")
    if not os.path.isfile(so):
        print(f"FAIL: libsystemd.so not found: {so}", file=sys.stderr)
        return 1
    if not _is_elf_shared_object(so):
        print(f"FAIL: {so} is not a valid aarch64 ELF shared object", file=sys.stderr)
        return 1
    # 2) public header present
    hdr = os.path.join(pkg, "include", "systemd", "sd-bus.h")
    if not os.path.isfile(hdr):
        print(f"FAIL: sd-bus.h not found: {hdr}", file=sys.stderr)
        return 1
    # 3) static .dynsym export check (R34: real API present, no dlopen)
    ok, missing = _check_symbols(so, ["sd_bus_new", "sd_bus_default", "sd_bus_close"])
    if not ok:
        print(f"FAIL: .dynsym missing exported symbols: {missing}", file=sys.stderr)
        return 1

    print("OK: systemd libsystemd.so valid aarch64 ELF (ET_DYN/LE/EM_AARCH64) "
          "+ sd-bus.h + .dynsym exports (sd_bus_new/default/close) present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
