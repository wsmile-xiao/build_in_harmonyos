#!/usr/bin/env python3
"""callisto 1.1.0 consumer test — application package verification.

Checks the installed package: bin/callisto exists, is non-empty, is
executable, and -V executes (rc=0, version banner);
bin/callisto-sunschedule exists and is non-empty;
lib/pkgconfig/callisto.pc exists (L1e destructible artifact — breaking
bin/ must FAIL this test). Exits non-zero on any failure.
"""
import os
import subprocess
import sys


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    exe = os.path.join(pkg_root, "bin", "callisto")
    if not os.path.isfile(exe):
        print("[FAIL] bin/callisto missing")
        return 1
    if os.path.getsize(exe) == 0:
        print("[FAIL] bin/callisto empty")
        failures += 1
    else:
        print("[ok] bin/callisto present (%d bytes)" % os.path.getsize(exe))
    if not os.access(exe, os.X_OK):
        print("[FAIL] bin/callisto not executable")
        failures += 1
    else:
        print("[ok] bin/callisto executable")
    r = subprocess.run([exe, "-V"], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=10)
    out = (r.stdout + r.stderr).decode(errors="replace")
    if r.returncode != 0 or "e-Callisto for Unix 1.1.0" not in out:
        print("[FAIL] bin/callisto -V rc=%d out=%s"
              % (r.returncode, out[:200]))
        failures += 1
    else:
        print("[ok] bin/callisto -V rc=0 (version banner OK)")

    sched = os.path.join(pkg_root, "bin", "callisto-sunschedule")
    if not os.path.isfile(sched):
        print("[FAIL] bin/callisto-sunschedule missing")
        failures += 1
    elif os.path.getsize(sched) == 0:
        print("[FAIL] bin/callisto-sunschedule empty")
        failures += 1
    else:
        print("[ok] bin/callisto-sunschedule present (%d bytes)"
              % os.path.getsize(sched))

    pc = os.path.join(pkg_root, "lib", "pkgconfig", "callisto.pc")
    if not os.path.isfile(pc):
        print("[FAIL] lib/pkgconfig/callisto.pc missing")
        failures += 1
    else:
        print("[ok] lib/pkgconfig/callisto.pc present")

    if failures:
        print("callisto: %d assertion(s) failed" % failures)
        return 1
    print("callisto package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
