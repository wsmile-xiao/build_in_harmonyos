#!/usr/bin/env python3
"""debhelper consumer test (R34): dh script present + perl -c syntax check.
dh --version needs a debian/control dir (sandbox has none) — use perl -c."""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    dh = os.path.join(pkg, "bin", "dh")
    if not os.path.isfile(dh):
        print(f"FAIL: dh script missing: {dh}", file=sys.stderr)
        return 1
    perl = "/data/service/hnp/bin/perl"
    if not os.path.isfile(perl):
        perl = "perl"
    # dh uses Debian::Debhelper::Dh_Lib — PERL5LIB must include packaged perl5
    env = dict(os.environ)
    env["PERL5LIB"] = os.path.join(pkg, "lib", "perl5")
    r = subprocess.run([perl, "-c", dh], capture_output=True, text=True,
                       env=env)
    if r.returncode != 0:
        print(f"FAIL: dh syntax check: {r.stderr}", file=sys.stderr)
        return 1
    print("OK: dh script present + perl -c syntax check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
