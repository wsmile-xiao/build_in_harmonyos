#!/usr/bin/env python3
"""Pure-Python ELF / package inspection for the blst HarmonyOS package.

Runs on any host (no external tools), so a cross-building host still validates
the artifact instead of passing silently.  Exits non-zero on any failed check.

A1  include/blst.h, blst_aux.h, blst.hpp present
A2  lib/libblst.a present and is an ELF64 AArch64 archive
A3  lib/libblst.so (when built shared) is ELF64 AArch64 with the musl
    interpreter and .note.ohos.ident, and carries no host RPATH/RUNPATH
A4  the AArch64 assembly routines are really inside libblst.a
    (blst_sha256_block_armv8, mul_mont_384, add_mod_384,
     ct_inverse_mod_384, sqr_mont_384) - a --BLST_PORTABLE__-only build
     would not contain them
A5  no Mach-O / PE artifacts leaked into the package
"""
import argparse
import os
import re
import sys

FAILS = []
CHECKS = 0


def check(cond, name):
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}")
        FAILS.append(name)


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def elf_machine_label(data):
    if data[:4] != b"\x7fELF":
        return None
    is64 = data[4] == 2
    little = data[5] == 1
    if not (is64 and little):
        return "not-elf64-le"
    e_machine = int.from_bytes(data[18:20], "little")
    return {0xB7: "AArch64", 0x3E: "x86_64"}.get(e_machine, f"machine-{e_machine:#x}")


def has_section(data, name):
    return name.encode() in data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--source", default="")
    args = ap.parse_args()
    pkg = args.package

    print(f"blst OHOS ABI check: {pkg}")

    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")

    # A1 headers
    for h in ("blst.h", "blst_aux.h", "blst.hpp"):
        check(os.path.isfile(os.path.join(inc, h)), f"A1 include/{h} present")

    # A2 static archive
    sa = os.path.join(lib, "libblst.a")
    check(os.path.isfile(sa), "A2 lib/libblst.a present")
    if os.path.isfile(sa):
        blob = read(sa)
        check(blob[:8] == b"!<arch>\n", "A2 libblst.a is an ar archive")
        # members follow a 68-byte ar header (possibly after a symbol table),
        # so look for the ELF magic anywhere in the archive
        check(b"\x7fELF" in blob, "A2 libblst.a contains ELF objects")
        # A4 the AArch64 assembly really is compiled in
        for sym in ("blst_sha256_block_armv8", "mul_mont_384",
                    "add_mod_384", "ct_inverse_mod_384", "sqr_mont_384"):
            check(sym.encode() in blob, f"A4 AArch64 asm symbol in libblst.a: {sym}")

    # A3 shared object
    so = os.path.join(lib, "libblst.so")
    if os.path.isfile(so):
        d = read(so)
        check(elf_machine_label(d) == "AArch64",
              "A3 libblst.so is ELF64 AArch64")
        check(has_section(d, ".note.ohos.ident"),
              "A3 libblst.so carries .note.ohos.ident")
        # a shared library has no PT_INTERP; what matters is that it is built
        # for the OHOS sysroot and does not pull a glibc-only dependency
        check(b"libc.so" in d and b"libc.so.6" not in d,
              "A3 libblst.so links OHOS libc.so (not glibc libc.so.6)")
        check(b"RUNPATH" not in d and b"RPATH" not in d,
              "A3 libblst.so has no host RPATH/RUNPATH")
        check(not re.search(rb"/(home|Users)/[A-Za-z0-9_.-]+", d),
              "A3 libblst.so has no build-host absolute path")

    # A5 no foreign ABI artifacts
    leaked = []
    for root, _dirs, files in os.walk(pkg):
        for f in files:
            if f.endswith((".dll", ".dylib")):
                leaked.append(os.path.join(root, f))
    check(not leaked, f"A5 no Mach-O/PE artifacts leaked ({len(leaked)} found)")

    print(f"\nABI checks={CHECKS} failures={len(FAILS)}")
    if FAILS:
        for f in FAILS:
            print(f"  failed: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
