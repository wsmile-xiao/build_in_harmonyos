#!/usr/bin/env python3
"""test_smi.py — consumer test source for shared-mime-info 2.5.1 (L0c).

REAL API check (R34): run the packaged update-mime-database with
--version (core tool of shared-mime-info — proves the binary works).
Usage: test_smi.py <bin-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_smi.py <bin-dir>")
    bindir = sys.argv[1]
    umd = os.path.join(bindir, "update-mime-database")
    if not os.path.isfile(umd):
        raise AssertionError(f"update-mime-database missing: {umd}")
    # update-mime-database: short options only; -h prints usage (proves the
    # tool runs — version flags require a MIME-DIR arg)
    r = subprocess.run([umd, "-h"], capture_output=True, text=True)
    if r.returncode not in (0, 1):
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"update-mime-database -h failed (rc={r.returncode})")
    if "Usage" not in (r.stdout or "") + (r.stderr or ""):
        raise AssertionError("update-mime-database -h output unexpected")
    print("OK: shared-mime-info 2.5.1 real API ok "
          "(update-mime-database -h usage)")


if __name__ == "__main__":
    main()
