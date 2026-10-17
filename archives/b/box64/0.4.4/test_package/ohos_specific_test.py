#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R53 HarmonyOS-specific structural suite for box64 0.4.4 (pure python3).

No readelf/objdump dependency (CI workers may lack them): the ELF files are
parsed byte-by-byte with struct only.

Covered OHOS adaptation points:
  1. bin/box64 is ELF64 little-endian AArch64 with e_type=ET_EXEC -- the
     non-PIE link is part of the OHOS stabilization (the PIE build was not
     startable on this toolchain).
  2. PT_INTERP == /lib/ld-musl-aarch64.so.1 (OHOS musl runtime).
  3. .codesign section present (OHOS requires signed ELF images; cmake
     --install rewrites RUNPATH, so the package re-signs the binary).
  4. .dynsym exports none of the host wrappers (malloc/free/calloc/realloc/
     memalign/mmap/mmap64/munmap/dlopen/dlsym/dlclose/...).  On OHOS musl
     those exports make libc resolve its own PLT through the executable and
     call box64's not-yet-initialised wrappers -> SIGSEGV before main();
     the version script must keep them local.
  5. DT_NEEDED contains libfts.so.0 and libobstack.so.1; DT_RUNPATH contains
     $ORIGIN/../lib; both shared objects are bundled under <pkg>/lib, so the
     package is self-contained for its musl-compat dependencies.
  6. The generated x86_64 fixture really is ET_EXEC/EM_X86_64 and matches
     the expected 177-byte sha256 (the emulator input is an x86_64 program).

usage: python3 ohos_specific_test.py <package_folder> [hello_x86_64]
prints "ALL OHOS SPECIFIC TESTS PASSED (N assertions)" on success.
"""
import hashlib
import os
import struct
import sys

WRAPPER_EXPORTS = (
    "malloc", "free", "calloc", "realloc", "aligned_alloc", "memalign",
    "posix_memalign", "valloc", "malloc_usable_size", "mmap", "mmap64",
    "munmap", "dlopen", "dlclose", "dlsym",
)

HELLO_SHA256 = "170f6cb94332a64b416b383d274695bb635c462a57e9c138b2348e47637b6934"

_checks = 0
_failures = []


def check(cond, msg):
    global _checks
    _checks += 1
    if cond:
        print("  [ok] %s" % msg)
    else:
        print("  [FAIL] %s" % msg)
        _failures.append(msg)


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def u64(data, off):
    return struct.unpack_from("<Q", data, off)[0]


def _str(data, strtab, off):
    start = strtab["offset"] + off
    end = strtab["offset"] + strtab["size"]
    return data[start:end].split(b"\x00", 1)[0].decode("utf-8", "replace")


def parse_elf(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file: %s" % path)

    ei_class = data[4]
    ei_data = data[5]
    e_type = u16(data, 16)
    e_machine = u16(data, 18)
    e_phoff = u64(data, 32)
    e_shoff = u64(data, 40)
    e_phentsize = u16(data, 54)
    e_phnum = u16(data, 56)
    e_shentsize = u16(data, 58)
    e_shnum = u16(data, 60)
    e_shstrndx = u16(data, 62)

    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        phdrs.append(dict(
            type=u32(data, off), flags=u32(data, off + 4),
            offset=u64(data, off + 8), filesz=u64(data, off + 32)))

    shdrs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        shdrs.append(dict(
            name=u32(data, off), type=u32(data, off + 4),
            offset=u64(data, off + 24), size=u64(data, off + 32),
            link=u32(data, off + 40), entsize=u64(data, off + 56)))

    if e_shstrndx < len(shdrs):
        shtab = shdrs[e_shstrndx]
        for sh in shdrs:
            sh["sname"] = _str(data, shtab, sh["name"])
    else:
        for sh in shdrs:
            sh["sname"] = ""

    interp = None
    for p in phdrs:
        if p["type"] == 3:  # PT_INTERP
            raw = data[p["offset"]:p["offset"] + p["filesz"]]
            interp = raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
            break

    neededs = []
    runpaths = []
    exported = set()
    sections = [sh["sname"] for sh in shdrs]

    for sh in shdrs:
        if sh["link"] >= len(shdrs):
            continue
        strtab = shdrs[sh["link"]]
        if sh["type"] == 6:  # SHT_DYNAMIC
            for i in range(sh["size"] // 16):
                off = sh["offset"] + i * 16
                tag = u64(data, off)
                val = u64(data, off + 8)
                if tag == 1:  # DT_NEEDED
                    neededs.append(_str(data, strtab, val))
                elif tag in (15, 29):  # DT_RPATH / DT_RUNPATH
                    runpaths.append(_str(data, strtab, val))
        elif sh["type"] == 11:  # SHT_DYNSYM
            for i in range(sh["size"] // 24):
                off = sh["offset"] + i * 24
                st_name = u32(data, off)
                st_info = data[off + 4]
                st_shndx = u16(data, off + 6)
                bind = st_info >> 4
                if st_name == 0 or st_shndx == 0:
                    continue  # undefined imports are fine
                if bind in (1, 2):  # STB_GLOBAL / STB_WEAK
                    exported.add(_str(data, strtab, st_name))

    return dict(cls=ei_class, data_enc=ei_data, e_type=e_type,
                e_machine=e_machine, interp=interp, sections=sections,
                neededs=neededs, runpaths=runpaths, exported=exported)


def main():
    if len(sys.argv) < 2:
        print("usage: ohos_specific_test.py <package_folder> [hello_x86_64]")
        return 2
    pkg = sys.argv[1]
    hello = sys.argv[2] if len(sys.argv) > 2 else None

    box64 = os.path.join(pkg, "bin", "box64")
    print("[R53] OHOS-specific structural suite")
    print("      package : %s" % pkg)
    check(os.path.isfile(box64), "bin/box64 is packaged")

    elf = parse_elf(box64)
    check(elf["cls"] == 2 and elf["data_enc"] == 1,
          "ELFCLASS64 little-endian")
    check(elf["e_machine"] == 0xB7,
          "e_machine=AArch64 (0x%x)" % elf["e_machine"])
    check(elf["e_type"] == 2,
          "e_type=ET_EXEC (%d; non-PIE OHOS stabilization)" % elf["e_type"])
    check(elf["interp"] == "/lib/ld-musl-aarch64.so.1",
          "PT_INTERP=%s (OHOS musl)" % elf["interp"])
    check(".codesign" in elf["sections"], "ELF .codesign section present")

    leaked = [name for name in WRAPPER_EXPORTS if name in elf["exported"]]
    check(not leaked,
          "no host wrapper exports in .dynsym (leaked=%s)" % leaked)
    check("libfts.so.0" in elf["neededs"],
          "DT_NEEDED libfts.so.0 (neededs=%s)" % elf["neededs"])
    check("libobstack.so.1" in elf["neededs"],
          "DT_NEEDED libobstack.so.1 (neededs=%s)" % elf["neededs"])
    check(any("$ORIGIN/../lib" in p for p in elf["runpaths"]),
          "DT_RUNPATH contains $ORIGIN/../lib (runpaths=%s)" % elf["runpaths"])

    for soname in ("libfts.so.0", "libobstack.so.1"):
        check(os.path.isfile(os.path.join(pkg, "lib", soname)),
              "bundled %s under package lib/" % soname)

    if hello:
        h = parse_elf(hello)
        check(h["e_type"] == 2 and h["e_machine"] == 0x3E,
              "x86_64 fixture is ET_EXEC/EM_X86_64")
        digest = hashlib.sha256(open(hello, "rb").read()).hexdigest()
        check(digest == HELLO_SHA256,
              "x86_64 fixture sha256=%s" % digest[:16])

    print("")
    if _failures:
        print("OHOS SPECIFIC TESTS FAILED (%d/%d)" % (len(_failures), _checks))
        return 1
    print("ALL OHOS SPECIFIC TESTS PASSED (%d assertions)" % _checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
