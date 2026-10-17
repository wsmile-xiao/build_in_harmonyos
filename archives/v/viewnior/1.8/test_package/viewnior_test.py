#!/usr/bin/env python3
"""Exercise the packaged viewnior binary from a consumer's point of view.

Usage: viewnior_test.py <path-to-viewnior>

viewnior 1.8 is a GTK+2 image viewer.  It has no upstream test suite (no
tests/ directory, no meson test targets).  Patch 0001 adds a headless
early-exit for ``--version`` that prints PACKAGE_STRING ("viewnior 1.8")
before GTK opens the default X display, so the packaged binary is fully
verifiable on OHOS build workers that have no X server.

Consumer assertions:

1. the packaged binary is a genuine aarch64 ELF (e_machine=0xB7 — the OHOS
   target machine id, NOT a host/other-arch artifact);
2. running it resolves the *entire* GTK+2 shared-library closure — a missing
   libgtk-x11-2.0/libglib-2.0 or an ABI/symbol mismatch would surface as
   "Error loading shared library ..." / "undefined symbol" first;
3. ``viewnior --version`` prints "viewnior 1.8" and exits 0 (the headless
   path introduced by patch 0001).
"""
import os
import struct
import subprocess
import sys

EXPECTED_VERSION = "viewnior 1.8"

checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def main():
    if len(sys.argv) != 2:
        print("usage: %s <path-to-viewnior>" % sys.argv[0], file=sys.stderr)
        return 2

    binary = sys.argv[1]
    check(os.path.isfile(binary), "viewnior binary not found: %s" % binary)
    check(os.access(binary, os.X_OK), "viewnior is not executable")

    # 1) Genuine aarch64 (OHOS) ELF, not a host build artifact.
    with open(binary, "rb") as fh:
        head = fh.read(20)
    check(head[:4] == b"\x7fELF", "not an ELF binary")
    check(head[4] == 2, "not a 64-bit ELF")
    machine = struct.unpack("<H", head[18:20])[0]
    check(machine == 0xB7, "not an aarch64 ELF (e_machine=%#x)" % machine)
    print("aarch64 ELF verified (e_machine=0xB7, OHOS target)")

    # 2) The whole GTK+2 closure must resolve when the binary runs.
    version = subprocess.run([binary, "--version"],
                             capture_output=True, text=True, timeout=60)
    vtext = (version.stdout or "") + (version.stderr or "")
    for bad in ("Error loading shared library", "symbol not found",
                "undefined symbol", "error while loading shared libraries"):
        check(bad not in vtext, "dynamic link failure: %s" % vtext)

    # 3) Headless --version prints the version and exits 0.
    check(version.returncode == 0, "--version rc=%d: %s" % (version.returncode, vtext))
    check(EXPECTED_VERSION in vtext,
          "--version did not print %r: %r" % (EXPECTED_VERSION, vtext))
    print("viewnior --version -> %s (rc=0)" % EXPECTED_VERSION)

    # 4) Plain --help (no display): GOption's gtk option group still needs the
    # X display, so the run must at least resolve the whole GTK+2 closure and
    # fail only at display initialisation — never at dynamic-link time.
    help_run = subprocess.run([binary, "--help"],
                              capture_output=True, text=True, timeout=60)
    htext = (help_run.stdout or "") + (help_run.stderr or "")
    for bad in ("Error loading shared library", "symbol not found",
                "undefined symbol", "error while loading shared libraries"):
        check(bad not in htext, "dynamic link failure (--help): %s" % htext)
    if help_run.returncode == 0:
        print("viewnior --help OK")
    else:
        # Headless: GTK cannot open the display (expected), nothing else failed.
        check("display" in htext.lower(),
              "--help failed for an unexpected reason: %r" % htext)
        print("viewnior --help -> display init failure as expected (headless)")

    print("viewnior consumer smoke: %d/%d checks passed" % (checks, checks))
    print("VIEWNIOR-CONSUMER-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
