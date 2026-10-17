#!/usr/bin/env python3
"""Static ELF verification for the packaged libsbig shared library.

R34/L0d consumer test that does NOT dlopen/link-run the delivered .so.

Why static: OHOS uses musl libc, but the upstream libsbig blob is a glibc
build (DT_NEEDED: libm.so.6 / libudev.so.1 / libc.so.6 /
ld-linux-aarch64.so.1).  OHOS has no glibc loader (only ld-musl-aarch64.so.1,
libc soname is "libc.so"), so a runtime dlopen/link-run cannot succeed here.
ELF signing (binary-sign-tool) only clears the E318 "unsigned ELF rejected"
gate — it does not provide glibc symbols, so it cannot make the glibc blob
loadable on musl.

This test therefore statically verifies the delivered artifact instead:
  - ELF type == ET_DYN, machine == AArch64 (the packaged arch)
  - SONAME == libsbig.so.4 (runtime link contract)
  - exported symbol SBIGUnivDrvCommand present (real driver entry point)
  - DT_NEEDED libudev.so.1 present (consumer dependency contract)

Usage: python3 check_elf.py <path-to-libsbig.so>
Exit 0 on success, non-zero (with a message) on any failed check.
"""
import struct
import sys

# ELF constants
ET_DYN = 3
EM_AARCH64 = 183
SHT_DYNSYM = 11
SHT_STRTAB = 3
SHN_UNDEF = 0

EXPECTED_SYMBOLS = ("SBIGUnivDrvCommand",)
EXPECTED_NEEDED = ("libudev.so.1",)

# 64-bit ELF section header:
# sh_name(4) sh_type(4) sh_flags(8) sh_addr(8) sh_offset(8) sh_size(8)
# sh_link(4) sh_info(4) sh_addralign(8) sh_entsize(8)


def check(path):
    with open(path, "rb") as fh:
        data = fh.read()

    if data[:4] != b"\x7fELF":
        raise AssertionError("not an ELF file")
    if data[4] != 2:                      # EI_CLASS: 64-bit
        raise AssertionError(f"not a 64-bit ELF (EI_CLASS={data[4]})")
    if data[5] != 1:                      # EI_DATA: little-endian
        raise AssertionError(f"not little-endian (EI_DATA={data[5]})")

    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    if e_type != ET_DYN:
        raise AssertionError(f"ELF type {e_type} != ET_DYN (shared object)")
    if e_machine != EM_AARCH64:
        raise AssertionError(f"ELF machine {e_machine} != AArch64 (183)")

    e_shoff = struct.unpack_from("<Q", data, 40)[0]
    e_shentsize = struct.unpack_from("<H", data, 58)[0]
    e_shnum = struct.unpack_from("<H", data, 60)[0]
    e_shstrndx = struct.unpack_from("<H", data, 62)[0]

    if e_shoff == 0 or e_shnum == 0 or e_shentsize < 64:
        raise AssertionError("no usable section header table")

    # shstrtab (string table for section names) — not strictly required.
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_type, = struct.unpack_from("<I", data, off + 4)
        sh_offset, = struct.unpack_from("<Q", data, off + 24)
        sh_size, = struct.unpack_from("<Q", data, off + 32)
        sections.append((sh_type, sh_offset, sh_size))

    dynsym = None
    dynstr = None
    for sh_type, sh_offset, sh_size in sections:
        if sh_type == SHT_DYNSYM:
            dynsym = (sh_offset, sh_size)
        elif sh_type == SHT_STRTAB:
            # .dynstr is the strtab whose content is referenced by DT_*;
            # pick the one that contains our expected symbol names.
            try:
                blob = data[sh_offset:sh_offset + sh_size]
            except Exception:
                blob = b""
            if b"libudev.so.1" in blob or b"libsbig.so.4" in blob:
                dynstr = (sh_offset, sh_size)

    if dynsym is None:
        raise AssertionError("no .dynsym section found")
    if dynstr is None:
        raise AssertionError("no .dynstr section found")

    sym_off, sym_size = dynsym
    str_off, str_size = dynstr
    entsize = 24  # Elf64_Sym

    def cstr(off):
        end = data.index(b"\x00", off)
        return data[off:end].decode("utf-8", "replace")

    # --- SONAME + NEEDED from .dynamic ---
    dyn_off = dyn_size = None
    for sh_type, sh_offset, sh_size in sections:
        if sh_type == 6:  # SHT_DYNAMIC
            dyn_off, dyn_size = sh_offset, sh_size
            break
    soname = None
    needed = []
    if dyn_off is not None:
        for j in range(0, dyn_size, 16):
            tag, val = struct.unpack_from("<qQ", data, dyn_off + j)
            if tag == 14:      # DT_SONAME
                soname = cstr(str_off + val)
            elif tag == 1:     # DT_NEEDED
                needed.append(cstr(str_off + val))
    else:
        # Fall back to scanning .dynstr for the soname token.
        pass

    if soname is None:
        raise AssertionError("no DT_SONAME found")
    if soname != "libsbig.so.4":
        raise AssertionError(f"SONAME '{soname}' != 'libsbig.so.4'")

    need_names = set(needed)
    for want in EXPECTED_NEEDED:
        if want not in need_names:
            raise AssertionError(
                f"DT_NEEDED missing '{want}' (got {sorted(need_names)})")

    # --- exported symbols from .dynsym ---
    exported = set()
    for off in range(sym_off, sym_off + sym_size, entsize):
        st_name, = struct.unpack_from("<I", data, off)
        st_shndx, = struct.unpack_from("<H", data, off + 6)
        if st_shndx == SHN_UNDEF:
            continue
        if st_name == 0 or st_name >= str_size:
            continue
        exported.add(cstr(str_off + st_name))

    for want in EXPECTED_SYMBOLS:
        if want not in exported:
            raise AssertionError(
                f"exported symbol '{want}' not found (got {len(exported)} symbols)")

    print(f"OK: {path}")
    print(f"    SONAME = {soname}")
    print(f"    DT_NEEDED = {sorted(need_names)}")
    print(f"    exported {len(exported)} symbols, incl. {', '.join(EXPECTED_SYMBOLS)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: check_elf.py <path-to-libsbig.so>", file=sys.stderr)
        sys.exit(2)
    try:
        check(sys.argv[1])
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
