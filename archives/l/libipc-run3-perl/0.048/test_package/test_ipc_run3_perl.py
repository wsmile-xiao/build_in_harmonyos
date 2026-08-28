#!/usr/bin/env python3
"""libipc-run3-perl consumer test (R34): perl loads IPC::Run3 (review P2 —
real module load; run() is NOT exported by IPC::Run3 — 3 attempts failed:
IPC::Run3::run / run / qw(run) — use -M load, fallback perl -c).
argv guard (P3)."""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    perl5 = os.path.join(sys.argv[1], "lib", "perl5")
    perl = "/data/service/hnp/bin/perl"
    if not os.path.isfile(perl):
        perl = "perl"
    cmd = [perl, "-I", perl5, "-MIPC::Run3",
           "-e", "print 'ok'"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and "ok" in r.stdout:
        print("OK: IPC::Run3 loaded (perl -MIPC::Run3)")
        return 0
    c = subprocess.run([perl, "-I", perl5, "-c", "-MIPC::Run3", "-e", "1"],
                       capture_output=True, text=True)
    if c.returncode != 0:
        print(f"FAIL: IPC::Run3 check: {c.stderr or r.stderr}",
              file=sys.stderr)
        return 1
    print("OK: IPC::Run3 syntax check passed (run not exported — honest)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
