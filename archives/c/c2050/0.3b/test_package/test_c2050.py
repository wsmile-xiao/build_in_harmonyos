#!/usr/bin/env python3
"""c2050 0.3b consumer test — application package verification.

Checks the installed package: bin/c2050 exists, is non-empty, is
executable, and executes with empty input (rc=0, main->LexPrint read
loop); bin/ps2lexmark exists and is non-empty;
lib/pkgconfig/c2050.pc exists (L1e destructible artifact — breaking
bin/ must FAIL this test). Exits non-zero on any failure.
"""
import os
import subprocess
import sys


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    exe = os.path.join(pkg_root, "bin", "c2050")
    if not os.path.isfile(exe):
        print("[FAIL] bin/c2050 missing")
        return 1
    if os.path.getsize(exe) == 0:
        print("[FAIL] bin/c2050 empty")
        failures += 1
    else:
        print("[ok] bin/c2050 present (%d bytes)" % os.path.getsize(exe))
    if not os.access(exe, os.X_OK):
        print("[FAIL] bin/c2050 not executable")
        failures += 1
    else:
        print("[ok] bin/c2050 executable")
    r = subprocess.run([exe], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=10)
    if r.returncode != 0:
        print("[FAIL] bin/c2050 empty-input run rc=%d err=%s"
              % (r.returncode, r.stderr.decode(errors="replace")[:200]))
        failures += 1
    else:
        print("[ok] bin/c2050 empty-input run rc=0 (main loop OK)")

    wrapper = os.path.join(pkg_root, "bin", "ps2lexmark")
    if not os.path.isfile(wrapper):
        print("[FAIL] bin/ps2lexmark missing")
        failures += 1
    elif os.path.getsize(wrapper) == 0:
        print("[FAIL] bin/ps2lexmark empty")
        failures += 1
    else:
        print("[ok] bin/ps2lexmark present (%d bytes)"
              % os.path.getsize(wrapper))

    pc = os.path.join(pkg_root, "lib", "pkgconfig", "c2050.pc")
    if not os.path.isfile(pc):
        print("[FAIL] lib/pkgconfig/c2050.pc missing")
        failures += 1
    else:
        print("[ok] lib/pkgconfig/c2050.pc present")

    if failures:
        print("c2050: %d assertion(s) failed" % failures)
        return 1
    print("c2050 package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
