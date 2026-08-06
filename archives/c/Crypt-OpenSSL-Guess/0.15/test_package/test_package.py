#!/usr/bin/env python3
"""Test source file for Crypt::OpenSSL::Guess test_package.

Verifies that the package contains the Guess.pm file with correct version.

Usage: python3 test_package.py <pm_path>
"""
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pm_path>", file=sys.stderr)
        sys.exit(1)

    pm_path = sys.argv[1]
    errors = []

    if not os.path.exists(pm_path):
        errors.append(f"Guess.pm not found at {pm_path}")
    else:
        with open(pm_path, "r") as f:
            content = f.read()
            if "0.15" not in content:
                errors.append("Guess.pm does not contain version 0.15")
            if "Crypt::OpenSSL::Guess" not in content:
                errors.append("Guess.pm does not contain package name Crypt::OpenSSL::Guess")
            if "openssl_inc_paths" not in content:
                errors.append("Guess.pm does not export openssl_inc_paths function")
            if "openssl_lib_paths" not in content:
                errors.append("Guess.pm does not export openssl_lib_paths function")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: Crypt::OpenSSL::Guess package verified - Guess.pm (version 0.15, exports correct)")
    sys.exit(0)


if __name__ == "__main__":
    main()
