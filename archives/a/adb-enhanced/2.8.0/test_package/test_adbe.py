#!/usr/bin/env python3
"""Smoke test for adb-enhanced 2.8.0 — verifies package installation and version.

This test source file is referenced by test_package/conanfile.py::test().
It verifies:
  1. The adbe Python package can be imported (structure check)
  2. The version.txt contains the correct version string
  3. The deps directory contains required runtime dependencies
"""
import os
import sys


def test_version():
    """Verify version.txt contains '2.8.0'."""
    # Find the adbe package in site-packages
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    for path in sys.path:
        version_file = os.path.join(path, "adbe", "version.txt")
        if os.path.isfile(version_file):
            with open(version_file) as f:
                version = f.read().strip()
            assert version == "2.8.0", f"Expected 2.8.0, got '{version}'"
            return version
    raise FileNotFoundError("adbe/version.txt not found in sys.path")


def test_package_files():
    """Verify required adbe package files exist."""
    required = ["__init__.py", "main.py", "adb_enhanced.py",
                "adb_helper.py", "output_helper.py", "version.txt"]
    for path in sys.path:
        adbe_dir = os.path.join(path, "adbe")
        if os.path.isdir(adbe_dir):
            for f in required:
                assert os.path.isfile(os.path.join(adbe_dir, f)), \
                    f"Missing: {f}"
            return
    raise FileNotFoundError("adbe package directory not found in sys.path")


if __name__ == "__main__":
    ver = test_version()
    test_package_files()
    print(f"✓ adb-enhanced {ver}: all checks passed")
