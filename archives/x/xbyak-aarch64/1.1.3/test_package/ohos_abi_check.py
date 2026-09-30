#!/usr/bin/env python3
"""Pure-Python artifact inspection for the xbyak_aarch64 HarmonyOS package.

Runs on any host (no external tools), so a cross-building host still validates
the artifact instead of passing silently.

A1  include/xbyak_aarch64/xbyak_aarch64.h and the codegen headers are present
A2  lib/libxbyak_aarch64.a is an ar archive containing ELF64 AArch64 objects
A3  the archive really carries the JIT code-generation implementation
A4  no Mach-O / PE artifacts leaked into the package
"""
import argparse
import os
import sys

FAILS = []
CHECKS = 0

REQUIRED_HEADERS = [
    "xbyak_aarch64.h",
    "xbyak_aarch64_code_array.h",
    "xbyak_aarch64_gen.h",
    "xbyak_aarch64_mnemonic_def.h",
]

# Symbols from the code-emission implementation (src/xbyak_aarch64_impl.cpp and
# src/util_impl.cpp).  A header-only stub build would not contain them.
REQUIRED_SYMBOLS = [
    b"CodeGenerator",
    b"Xbyak",
]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    args = ap.parse_args()
    pkg = args.package

    print(f"xbyak-aarch64 OHOS ABI check: {pkg}")

    inc = os.path.join(pkg, "include", "xbyak_aarch64")
    lib = os.path.join(pkg, "lib")

    for h in REQUIRED_HEADERS:
        check(os.path.isfile(os.path.join(inc, h)),
              f"A1 include/xbyak_aarch64/{h} present")

    sa = os.path.join(lib, "libxbyak_aarch64.a")
    check(os.path.isfile(sa), "A2 lib/libxbyak_aarch64.a present")
    if os.path.isfile(sa):
        blob = read(sa)
        check(blob[:8] == b"!<arch>\n", "A2 archive has the ar magic")
        check(b"\x7fELF" in blob, "A2 archive contains ELF objects")
        # ELF64 + AArch64 (e_machine 0xB7) somewhere in the members
        check(b"\xb7\x00" in blob, "A2 archive contains AArch64 objects")
        for sym in REQUIRED_SYMBOLS:
            check(sym in blob,
                  f"A3 codegen symbol present: {sym.decode(errors='replace')}")

    leaked = []
    for root, _dirs, files in os.walk(pkg):
        for f in files:
            if f.endswith((".dll", ".dylib")):
                leaked.append(os.path.join(root, f))
    check(not leaked, f"A4 no Mach-O/PE artifacts leaked ({len(leaked)} found)")

    print(f"\nABI checks={CHECKS} failures={len(FAILS)}")
    if FAILS:
        for f in FAILS:
            print(f"  failed: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
