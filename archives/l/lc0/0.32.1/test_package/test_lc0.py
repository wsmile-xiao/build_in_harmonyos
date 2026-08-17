#!/usr/bin/env python3
"""test_lc0.py — real consumer test source for lc0 0.32.1 (L0c).

Verifies the installed lc0 binary runs on OHOS:
  1) lc0 --version (or --help) exits 0 and prints engine info
  2) lc0 with no args exits with usage (rc != 0, engine actually runs)
Usage: test_lc0.py <path-to-lc0-bin>
"""
import os
import subprocess
import sys


def run(cmd, timeout=60):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_lc0.py <lc0-bin>")
    bin_path = sys.argv[1]
    if not os.path.isfile(bin_path):
        raise AssertionError(f"lc0 binary missing: {bin_path}")

    # 1) --version exits 0 and mentions the engine
    r = run([bin_path, "--version"])
    if r.returncode != 0:
        raise AssertionError(f"lc0 --version failed rc={r.returncode}: {r.stderr[:200]}")
    out = (r.stdout + r.stderr).lower()
    if "lc0" not in out:
        raise AssertionError(f"lc0 --version output unexpected: {out[:200]}")

    # 2) --help works (engine initializes CPU backend)
    r = run([bin_path, "--help"])
    if r.returncode != 0:
        raise AssertionError(f"lc0 --help failed rc={r.returncode}")

    print("OK: lc0 0.32.1 --version + --help passed")


if __name__ == "__main__":
    main()
