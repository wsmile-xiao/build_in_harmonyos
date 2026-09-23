#!/usr/bin/env python3
"""Test script for netdata Conan package.

Checks:
1. Binary exists in package
2. Binary is executable
3. `netdata -v` reports correct version
"""
import os
import sys
import subprocess
import glob


def find_netdata_binary(pkg_dir):
    """Find the netdata binary in common install locations."""
    search_paths = [
        os.path.join(pkg_dir, "sbin", "netdata"),
        os.path.join(pkg_dir, "bin", "netdata"),
        os.path.join(pkg_dir, "usr", "sbin", "netdata"),
        os.path.join(pkg_dir, "usr", "bin", "netdata"),
    ]
    for path in search_paths:
        if os.path.isfile(path):
            return path
    # Fallback: glob search
    matches = glob.glob(os.path.join(pkg_dir, "**", "netdata"), recursive=True)
    for m in matches:
        if os.path.isfile(m) and os.access(m, os.X_OK):
            return m
    return None


def main():
    if len(sys.argv) < 2:
        print("ERROR: package folder argument required", file=sys.stderr)
        sys.exit(1)

    pkg_dir = sys.argv[1]
    binary = find_netdata_binary(pkg_dir)

    if not binary:
        print(f"FAIL: netdata binary not found in {pkg_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found binary: {binary}")

    # Check executable
    if not os.access(binary, os.X_OK):
        print(f"FAIL: {binary} is not executable", file=sys.stderr)
        sys.exit(1)

    # Check version (must exit 0 and report the expected version)
    try:
        result = subprocess.run(
            [binary, "-v"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"FAIL: netdata -v exited with {result.returncode}",
                  file=sys.stderr)
            sys.exit(1)
        output = (result.stdout + result.stderr).strip()
        print(f"Version output: {output}")
        if "1.47.5" in output:
            print("PASS: netdata version matches")
            sys.exit(0)
        else:
            print(f"FAIL: version mismatch, expected 1.47.5, got: {output}",
                  file=sys.stderr)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print("FAIL: netdata -v timed out", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FAIL: cannot run netdata -v: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
