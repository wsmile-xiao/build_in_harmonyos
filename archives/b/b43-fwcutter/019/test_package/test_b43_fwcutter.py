#!/usr/bin/env python3
"""Test script for b43-fwcutter 019 — verifies firmware extraction tool works.

Tests:
  1. Binary exists and is executable (exit code check)
  2. Usage help — running with no args should print usage and exit non-zero
  3. Version — usage output should contain version 019
  4. List mode — running with -l should list supported driver files
  5. Identify mode — running with -i on a non-existent file should print an error gracefully
"""
import subprocess
import sys
import os


def main():
    fwcutter = sys.argv[1]

    # Test 1: Binary exists
    if not os.path.isfile(fwcutter):
        print(f"FAIL: Binary not found at {fwcutter}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: Binary exists at {fwcutter}")

    # Test 2: Usage help — no args should show usage and exit non-zero
    r = subprocess.run([fwcutter], capture_output=True, text=True, timeout=10)
    combined = r.stdout + r.stderr
    if r.returncode == 0:
        print(f"FAIL: Expected non-zero exit code for no args, got {r.returncode}", file=sys.stderr)
        sys.exit(1)
    if "usage" not in combined.lower() and "b43-fwcutter" not in combined.lower():
        print(f"FAIL: Expected usage info in output, got: {combined[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: No-args usage output")

    # Test 3: Version check
    if "019" not in combined:
        print(f"FAIL: Expected version 019 in output, got: {combined[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: Version 019 found in output")

    # Test 4: List mode — -l should list supported driver files
    r2 = subprocess.run([fwcutter, "-l"], capture_output=True, text=True, timeout=10)
    if r2.returncode != 0:
        print(f"FAIL: -l exited with {r2.returncode}", file=sys.stderr)
        sys.exit(1)
    if len(r2.stdout.strip()) < 10:
        print(f"FAIL: Expected driver file list from -l, got: {r2.stdout[:200]}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: -l lists supported drivers ({len(r2.stdout.strip().splitlines())} entries)")

    # Test 5: Graceful error on missing file
    r3 = subprocess.run(
        [fwcutter, "-i", "/nonexistent/file.o"],
        capture_output=True, text=True, timeout=10,
    )
    if r3.returncode == 0:
        print(f"FAIL: Expected non-zero exit for missing file", file=sys.stderr)
        sys.exit(1)
    print("PASS: Graceful error on missing input file")

    print("\nAll 5 tests passed!")


if __name__ == "__main__":
    main()
