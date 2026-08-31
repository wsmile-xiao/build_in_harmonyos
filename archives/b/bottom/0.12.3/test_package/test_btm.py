#!/usr/bin/env python3
"""Test script for bottom (btm) — verifies binary functionality.

This script is called by test_package/conanfile.py to verify
that the btm binary works correctly after Conan packaging.
"""

import subprocess
import sys


def test_btm_version(binary_path):
    """Run btm --version and verify output."""
    result = subprocess.run(
        [binary_path, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"FAIL: btm --version exited with {result.returncode}", file=sys.stderr)
        return False
    if "bottom" not in result.stdout.lower():
        print(f"FAIL: expected 'bottom' in output, got: {result.stdout}", file=sys.stderr)
        return False
    print(f"PASS: btm --version output: {result.stdout.strip()}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_btm.py <path-to-btm-binary>", file=sys.stderr)
        sys.exit(1)
    ok = test_btm_version(sys.argv[1])
    sys.exit(0 if ok else 1)
