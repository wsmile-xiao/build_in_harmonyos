#!/usr/bin/env python3
"""Test script for buku 5.0 — binary smoke test (R34).

buku is a CLI tool (application), not a library. The test verifies
the binary runs correctly via subprocess rather than Python import,
because the buku module location depends on setup.py install layout
which is package-internal.
"""
import subprocess
import sys


def test_version():
    """Verify buku --version returns the correct version."""
    try:
        result = subprocess.run(
            ["buku", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"FAIL: buku --version returned code {result.returncode}", file=sys.stderr)
            return False
        output = result.stdout.strip()
        if "5.0" in output:
            print(f"PASS: buku version = {output}")
            return True
        else:
            print(f"FAIL: unexpected version output: {output}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"FAIL: buku --version error: {e}", file=sys.stderr)
        return False


def test_help():
    """Verify buku --help works and shows usage."""
    try:
        result = subprocess.run(
            ["buku", "--help"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"FAIL: buku --help returned code {result.returncode}", file=sys.stderr)
            return False
        output = (result.stdout + result.stderr).lower()
        if "usage" in output or "bookmark" in output:
            print("PASS: buku --help shows usage")
            return True
        else:
            print(f"FAIL: buku --help unexpected output", file=sys.stderr)
            return False
    except Exception as e:
        print(f"FAIL: buku --help error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    results = [test_version(), test_help()]
    if all(results):
        print("\nAll buku tests passed.")
        sys.exit(0)
    else:
        failed = sum(1 for r in results if not r)
        print(f"\n{failed} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
