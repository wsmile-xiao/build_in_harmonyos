#!/usr/bin/env python3
"""cdrom-retriever 1.70 consumer test — script package verification.

Checks the installed package: lib/debian-installer/retriever exists, is
non-empty, is executable, parses with `sh -n` (real POSIX syntax check),
and lib/pkgconfig/cdrom-retriever.pc exists (L1e destructible artifact —
breaking lib/ must FAIL this test). Exits non-zero on any failure.
"""
import os
import shutil
import subprocess
import sys

RETRIEVER = os.path.join("lib", "debian-installer", "retriever")
PC = os.path.join("lib", "pkgconfig", "cdrom-retriever.pc")

# The conan test env PATH may not carry /usr/bin; locate a POSIX shell
# explicitly before running `sh -n`.
SHELL = shutil.which("sh") or "/usr/bin/sh"


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    script = os.path.join(pkg_root, RETRIEVER)
    if not os.path.isfile(script):
        print("[FAIL] %s missing" % script)
        return 1
    if os.path.getsize(script) == 0:
        print("[FAIL] %s empty" % RETRIEVER)
        failures += 1
    else:
        print("[ok] %s present (%d bytes)" % (RETRIEVER, os.path.getsize(script)))
    if not os.access(script, os.X_OK):
        print("[FAIL] %s not executable" % RETRIEVER)
        failures += 1
    else:
        print("[ok] %s executable" % RETRIEVER)
    r = subprocess.run([SHELL, "-n", script], capture_output=True)
    if r.returncode != 0:
        print("[FAIL] %s sh -n failed: %s"
              % (RETRIEVER, r.stderr.decode(errors="replace").strip()))
        failures += 1
    else:
        print("[ok] %s POSIX syntax OK (sh -n)" % RETRIEVER)

    pc = os.path.join(pkg_root, PC)
    if not os.path.isfile(pc):
        print("[FAIL] %s missing" % PC)
        failures += 1
    else:
        print("[ok] %s present" % PC)

    if failures:
        print("cdrom-retriever: %d assertion(s) failed" % failures)
        return 1
    print("cdrom-retriever package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
