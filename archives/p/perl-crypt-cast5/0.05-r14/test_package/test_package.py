#!/usr/bin/env python3
"""Test script for Crypt::CAST5 package verification.
Verifies that the package contains valid ELF .so and correct .pm file.

Usage: python3 test_package.py <so_path> <pm_path>
"""
import sys
import os

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_package.py <so_path> <pm_path>", file=sys.stderr)
        sys.exit(1)

    so_path = sys.argv[1]
    pm_path = sys.argv[2]

    errors = []

    # Check CAST5.so exists and is valid ELF
    if not os.path.exists(so_path):
        errors.append(f"CAST5.so not found at {so_path}")
    else:
        with open(so_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                errors.append(f"CAST5.so is not valid ELF (magic: {magic})")

    # Check CAST5.pm exists and has version
    if not os.path.exists(pm_path):
        errors.append(f"CAST5.pm not found at {pm_path}")
    else:
        with open(pm_path, "r") as f:
            content = f.read()
            if "0.05" not in content:
                errors.append("CAST5.pm does not contain version 0.05")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print("OK: Crypt::CAST5 package verified - CAST5.so (ELF valid), CAST5.pm (version 0.05)")
    sys.exit(0)

if __name__ == "__main__":
    main()
