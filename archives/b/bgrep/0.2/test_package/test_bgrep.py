#!/usr/bin/env python3
"""Test script for bgrep 0.2 — verifies binary search functionality.

Creates a binary file with a known hex pattern (DEADBEEF at offset 16),
runs bgrep to search for it, and verifies the output contains the
correct offset. Also tests wildcard search and stdin search.
"""
import subprocess
import sys
import os
import tempfile


def main():
    bgrep = sys.argv[1]

    # Create a binary file with DEADBEEF at offset 16
    test_file = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
    test_file.write(b'\x00' * 16)
    test_file.write(b'\xde\xad\xbe\xef')
    test_file.write(b'\x00' * 16)
    test_file.close()
    test_path = test_file.name

    try:
        # Test 1: Exact hex search — should find DEADBEEF at offset 0x10
        r = subprocess.run([bgrep, "deadbeef", test_path],
                          capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            print(f"FAIL: bgrep exited with {r.returncode}", file=sys.stderr)
            sys.exit(1)
        if "00000010" not in r.stdout:
            print(f"FAIL: Expected offset 00000010 in output, got: {r.stdout}", file=sys.stderr)
            sys.exit(1)
        print(f"PASS: exact hex search — found DEADBEEF at 0x10")

        # Test 2: Wildcard search — de??be should match deadbeef
        r2 = subprocess.run([bgrep, "de??be", test_path],
                           capture_output=True, text=True, timeout=10)
        if r2.returncode != 0:
            print(f"FAIL: wildcard search exited with {r2.returncode}", file=sys.stderr)
            sys.exit(1)
        if "00000010" not in r2.stdout:
            print(f"FAIL: Wildcard search expected 00000010, got: {r2.stdout}", file=sys.stderr)
            sys.exit(1)
        print(f"PASS: wildcard search — de??be matched at 0x10")

        # Test 3: No match — searching for a pattern not in the file
        r3 = subprocess.run([bgrep, "cafebabe", test_path],
                           capture_output=True, text=True, timeout=10)
        if r3.returncode != 0:
            print(f"FAIL: no-match search exited with {r3.returncode}", file=sys.stderr)
            sys.exit(1)
        if r3.stdout.strip():
            print(f"FAIL: Expected no output for missing pattern, got: {r3.stdout}", file=sys.stderr)
            sys.exit(1)
        print("PASS: no-match search — correctly returns empty output")

        # Test 4: Version check — running with no args should print version
        r4 = subprocess.run([bgrep], capture_output=True, text=True, timeout=10)
        if r4.returncode != 1:
            print(f"FAIL: Expected exit code 1 for no args, got {r4.returncode}", file=sys.stderr)
            sys.exit(1)
        if "0.2" not in r4.stderr:
            print(f"FAIL: Expected version 0.2 in stderr, got: {r4.stderr}", file=sys.stderr)
            sys.exit(1)
        print("PASS: version check — prints version 0.2 on no args")

        # Test 5: Stdin search
        r5 = subprocess.run([bgrep, "deadbeef"],
                           input=b'\x00' * 16 + b'\xde\xad\xbe\xef' + b'\x00' * 16,
                           capture_output=True, timeout=10)
        if r5.returncode != 0:
            print(f"FAIL: stdin search exited with {r5.returncode}", file=sys.stderr)
            sys.exit(1)
        if b"00000010" not in r5.stdout:
            print(f"FAIL: Expected offset 00000010 in stdin search, got: {r5.stdout}", file=sys.stderr)
            sys.exit(1)
        print("PASS: stdin search — found DEADBEEF at 0x10")

        print("\nAll 5 tests passed!")
    finally:
        os.unlink(test_path)


if __name__ == "__main__":
    main()
