#!/usr/bin/env python3
"""Test script for buckygen 1.1 — verifies the fullerene generator works.

Tests:
  1. Binary exists and is executable (exit code check)
  2. Usage help — running with no args should print usage and exit non-zero
  3. Generation — `buckygen 24 -u` should count fullerenes with 24 vertices
  4. Count line — output should contain the counter line with the expected count
"""
import subprocess
import sys
import os


def main():
    buckygen = sys.argv[1]

    # Test 1: Binary exists
    if not os.path.isfile(buckygen):
        print(f"FAIL: Binary not found at {buckygen}", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: Binary exists at {buckygen}")

    # Test 2: Usage help — no args should show usage and exit non-zero
    r = subprocess.run([buckygen], capture_output=True, text=True, timeout=10)
    combined = r.stdout + r.stderr
    if r.returncode == 0:
        print(f"FAIL: Expected non-zero exit code for no args, got {r.returncode}", file=sys.stderr)
        sys.exit(1)
    if "usage" not in combined.lower() and "buckygen" not in combined.lower():
        print(f"FAIL: Expected usage info in output, got: {combined[:200]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: No-args usage output")

    # Test 3: Generation — count fullerenes with 24 vertices (-u = count only)
    r2 = subprocess.run([buckygen, "24", "-u"], capture_output=True, text=True, timeout=120)
    out2 = r2.stdout + r2.stderr
    if r2.returncode != 0:
        print(f"FAIL: `buckygen 24 -u` exited with {r2.returncode}", file=sys.stderr)
        sys.exit(1)
    print("PASS: `buckygen 24 -u` ran (exit 0)")

    # Test 4: Count line — expected 89 fullerenes with 24 vertices
    if "Number of fullerenes generated with 24 vertices: 89" not in out2:
        print(f"FAIL: Expected count line 'Number of fullerenes generated with 24 vertices: 89', got: {out2[:300]}", file=sys.stderr)
        sys.exit(1)
    print("PASS: 24-vertex fullerene count = 89")

    print("\nAll 4 tests passed!")


if __name__ == "__main__":
    main()
