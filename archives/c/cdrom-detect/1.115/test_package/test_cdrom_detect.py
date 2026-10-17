#!/usr/bin/env python3
"""cdrom-detect 1.115 consumer test — script package verification.

Checks the installed package: the finish-install hook
lib/finish-install.d/15cdrom-detect exists, is non-empty, is executable
and passes a POSIX shell syntax parse (sh -n); and
lib/pkgconfig/cdrom-detect.pc exists (the L1e destructible artifact).
Exits non-zero on any failure.
"""
import os
import shutil
import subprocess
import sys

HOOK = os.path.join("lib", "finish-install.d", "15cdrom-detect")
PC = os.path.join("lib", "pkgconfig", "cdrom-detect.pc")

# The conan test env PATH may not carry /usr/bin; locate a POSIX shell
# explicitly before running `sh -n`.
SHELL = shutil.which("sh") or "/usr/bin/sh"


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    hook = os.path.join(pkg_root, HOOK)
    if not os.path.isfile(hook):
        print("[FAIL] %s missing" % hook)
        failures += 1
    else:
        if os.path.getsize(hook) == 0:
            print("[FAIL] %s empty" % hook)
            failures += 1
        else:
            print("[ok] %s present (%d bytes)" % (HOOK, os.path.getsize(hook)))
        if not os.access(hook, os.X_OK):
            print("[FAIL] %s not executable" % hook)
            failures += 1
        else:
            print("[ok] %s executable" % HOOK)
        r = subprocess.run([SHELL, "-n", hook], capture_output=True)
        if r.returncode != 0:
            print("[FAIL] %s sh -n parse failed: %s"
                  % (HOOK, r.stderr.decode(errors="replace").strip()))
            failures += 1
        else:
            print("[ok] %s sh -n POSIX syntax parse OK" % HOOK)

    pc = os.path.join(pkg_root, PC)
    if not os.path.isfile(pc):
        print("[FAIL] %s missing (L1e destructible artifact)" % pc)
        failures += 1
    else:
        print("[ok] lib/pkgconfig/cdrom-detect.pc present")

    if failures:
        print("cdrom-detect: %d assertion(s) failed" % failures)
        return 1
    print("cdrom-detect package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
