#!/usr/bin/env python3
"""readsb 3.16.15 test_package real test source (L0c: test source file).

Runs the installed readsb binary on OHOS:
1) --version assertion (binary runs, version correct)
2) startup behaviour with no input source: readsb correctly detects
   "No networking or SDR input selected" and exits rc=1 — proving the
   binary executes end-to-end without an SDR device (decode of live
   Mode-S requires hardware/network input, not available in CI).
Usage: test_readsb.py <path-to-readsb-bin>
"""
import os
import subprocess
import sys


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise AssertionError(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_readsb.py <readsb-bin>")
    rbin = sys.argv[1]
    if not os.path.isfile(rbin):
        raise AssertionError(f"readsb binary missing: {rbin}")

    # 1) version assertion (binary runs on OHOS)
    r = run([rbin, "--version"])
    if "3.16.15" not in r.stdout and "3.16.15" not in r.stderr:
        raise AssertionError(f"unexpected version output: {r.stdout!r}")

    # 2) no-input startup: readsb must detect missing input and exit rc=1
    #    with the expected message (proves the binary executes correctly).
    r = subprocess.run(
        [rbin, "--no-interactive", "--raw"],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 1:
        raise AssertionError(
            f"readsb no-input exit rc={r.returncode}, expected 1: {r.stderr!r}")
    if "No networking or SDR input selected" not in r.stderr:
        raise AssertionError(f"unexpected no-input message: {r.stderr!r}")
    print("OK: readsb 3.16.15 --version + no-input startup behaviour passed")


if __name__ == "__main__":
    main()
