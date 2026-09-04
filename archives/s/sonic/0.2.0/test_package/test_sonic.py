#!/usr/bin/env python3
"""Conan test_package for sonic — R34 real API usage (no empty shell).

sonic ships a CLI (`bin/sonic`, a wave speed/pitch/rate/volume tool) plus
libsonic.so.0.2.0 under <pkg>/lib/. The verifiable artifacts here are:
- bin/sonic exists and is a valid ELF executable (checked via ELF magic
  bytes, no external `file` binary — the OHOS sandbox has no `file` cmd);
- running `sonic` with no args prints the usage (real CLI behavior);
- lib/libsonic.so.0.2.0 exists and is a valid ELF shared object.
"""
import os
import struct
import subprocess
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


def main():
    pkg = sys.argv[1]
    # 1) CLI exists + is ELF
    cli = os.path.join(pkg, "bin", "sonic")
    if not os.path.isfile(cli):
        print(f"FAIL: sonic CLI not found: {cli}", file=sys.stderr)
        return 1
    if not _is_elf(cli):
        print(f"FAIL: {cli} is not an ELF executable", file=sys.stderr)
        return 1
    # 2) real CLI behavior: no-args prints usage
    try:
        proc = subprocess.run([cli], capture_output=True, text=True, timeout=10)
        out = (proc.stdout or "") + (proc.stderr or "")
        if "Usage" not in out and "Usage" not in out.lower():
            print(f"FAIL: sonic no-args did not print usage (rc={proc.returncode})",
                  file=sys.stderr)
            return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: sonic run failed: {exc}", file=sys.stderr)
        return 1
    # 3) libsonic shared object present + valid ELF shared object
    so = os.path.join(pkg, "lib", "libsonic.so.0.2.0")
    if not os.path.isfile(so):
        print(f"FAIL: libsonic.so.0.2.0 not found: {so}", file=sys.stderr)
        return 1
    if not _is_elf(so, want_so=True):
        print(f"FAIL: {so} is not an ELF shared object", file=sys.stderr)
        return 1

    print("OK: sonic CLI present + runs (usage) + libsonic.so.0.2.0 present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
