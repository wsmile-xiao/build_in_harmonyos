#!/usr/bin/env python3
"""Consumer test for the simulavr CLI (R34).

Two real checks, so a stub package or a dropped static registration cannot
pass:

1. ``simulavr -V`` starts and reports its version (the binary is present and
   runnable).
2. ``simulavr -d atmega128`` accepts the device name.  The AVR device models
   self-register at static-init time via ``AVR_REGISTER``; if the registrar
   objects were dropped from the static link, the CLI prints
   "Invalid device specification" instead — so this catches a functionally
   broken build that a mere ``--version`` check would miss.

Usage: test_simulavr.py <path-to-simulavr> <expected-version-string>
"""
import subprocess
import sys


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: test_simulavr.py <path-to-simulavr> <version-string>")
    exe, expect = sys.argv[1], sys.argv[2]

    r = subprocess.run([exe, "-V"], capture_output=True, text=True)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    print(out)
    if r.returncode != 0:
        raise SystemExit(f"simulavr -V exited {r.returncode}")
    if expect not in out:
        raise SystemExit(f"expected {expect!r} in version output")

    r2 = subprocess.run([exe, "-d", "atmega128"], capture_output=True,
                        text=True, timeout=30)
    dev = (r2.stdout or "") + (r2.stderr or "")
    if "Invalid device specification" in dev:
        raise SystemExit(
            "device atmega128 unknown — AVR_REGISTER registrars were dropped "
            "from the static link")
    print("OK: simulavr CLI runs and knows the atmega128 device")
    return 0


if __name__ == "__main__":
    sys.exit(main())
