#!/usr/bin/env python3
"""Test script for bootterm 0.5 — verifies the bt serial terminal binary.

Tests (each runs the real packaged binary and asserts observable behavior):
  1. Binary exists
  2. -V prints "BootTerm 0.5.0" banner and license, exits 0
  3. -h prints the full usage message, exits 0
  4. -l lists serial ports (table header) and exits 0 even with no ports

Note: bootterm prints the version banner, usage text and port list on
stderr (verified against upstream bt.c), so assertions use the combined
stdout+stderr stream.
"""
import subprocess
import sys
import os


def main():
    bt = sys.argv[1]

    # Test 1: Binary exists
    if not os.path.isfile(bt):
        print(f"FAIL: Binary not found at {bt}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: Binary exists at {bt}")

    def run_combined(args):
        r = subprocess.run([bt] + args, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout + r.stderr

    # Test 2: -V prints version banner and license, exits 0
    rc, out = run_combined(["-V"])
    if rc != 0:
        print(f"FAIL: -V exited with {rc}", file=sys.stderr)
        sys.exit(1)
    if "BootTerm 0.5.0" not in out:
        print(f"FAIL: Expected 'BootTerm 0.5.0' in -V output, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    if "Copyright" not in out:
        print(f"FAIL: Expected license line in -V output, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: -V prints version banner and license")

    # Test 3: -h prints the full usage message, exits 0
    rc, out = run_combined(["-h"])
    if rc != 0:
        print(f"FAIL: -h exited with {rc}", file=sys.stderr)
        sys.exit(1)
    if "Usage:" not in out:
        print(f"FAIL: Expected 'Usage:' in -h output, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    for opt in ("-l", "-b", "-V"):
        if f"  {opt}" not in out:
            print(f"FAIL: Expected option {opt} documented in -h output", file=sys.stderr)
            sys.exit(1)
    print("PASS: -h prints full usage message")

    # Test 4: -l lists ports table, exits 0 even with no serial ports
    rc, out = run_combined(["-l"])
    if rc != 0:
        print(f"FAIL: -l exited with {rc}", file=sys.stderr)
        sys.exit(1)
    if "port" not in out or "device" not in out or "driver" not in out:
        print(f"FAIL: Expected ports table header from -l, got: {out[:200]}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: -l prints ports table ({len(out.strip().splitlines())} lines)")

    print("\nAll 4 tests passed!")


if __name__ == "__main__":
    main()
