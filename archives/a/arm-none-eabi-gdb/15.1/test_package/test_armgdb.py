#!/usr/bin/env python3
"""test_armgdb.py — consumer test source for arm-none-eabi-gdb 15.1 (L0c).

REAL API check (R34): run the packaged arm-none-eabi-gdb with --version
and a -batch -ex command (startup + command execution prove usability).
Usage: test_armgdb.py <gdb-bin-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_armgdb.py <gdb-bin-dir>")
    bindir = sys.argv[1]
    gdb = os.path.join(bindir, "arm-none-eabi-gdb")
    if not os.path.isfile(gdb):
        raise AssertionError(f"gdb binary missing: {gdb}")
    r = subprocess.run([gdb, "--version"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"gdb --version failed (rc={r.returncode})")
    if "GNU gdb" not in (r.stdout or ""):
        raise AssertionError("gdb --version output unexpected")
    # batch command execution (real API surface)
    r2 = subprocess.run([gdb, "-batch", "-ex", "set architecture arm"],
                        capture_output=True, text=True)
    if r2.returncode != 0:
        sys.stderr.write(r2.stderr or "")
        raise SystemExit(f"gdb -batch failed (rc={r2.returncode})")
    print("OK: arm-none-eabi-gdb 15.1 real API ok (version + batch cmd)")


if __name__ == "__main__":
    main()
