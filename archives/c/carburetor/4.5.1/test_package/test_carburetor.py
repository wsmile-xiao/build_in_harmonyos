#!/usr/bin/env python3
"""Test source file for carburetor 4.5.1 conan test_package.

This file verifies that the carburetor package is correctly installed:
- Entry point script exists in bin/
- Python module __init__.py is present
- Desktop entry file is installed

Usage: Run via conan test_package (conanfile.py test() method calls self.run())
"""
import os
import sys
import glob


def test_entry_point(pkg_folder):
    """Verify the entry point script exists."""
    entry = os.path.join(pkg_folder, "bin", "carburetor")
    assert os.path.isfile(entry), f"Entry point not found: {entry}"
    print(f"[PASS] Entry point: {entry}")


def test_python_module(pkg_folder):
    """Verify the Python module structure is present."""
    inits = glob.glob(
        os.path.join(pkg_folder, "**", "carburetor", "__init__.py"),
        recursive=True
    )
    assert inits, "carburetor/__init__.py not found"
    print(f"[PASS] Python module: {inits[0]}")


def test_desktop_entry(pkg_folder):
    """Verify the desktop entry file is installed."""
    desktops = glob.glob(
        os.path.join(pkg_folder, "**", "applications",
                     "io.frama.tractor.carburetor.desktop"),
        recursive=True
    )
    assert desktops, "Desktop entry not found"
    print(f"[PASS] Desktop entry: {desktops[0]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: test_carburetor.py <package_folder>")
        sys.exit(1)
    pkg = sys.argv[1]
    test_entry_point(pkg)
    test_python_module(pkg)
    test_desktop_entry(pkg)
    print("[ALL PASS] carburetor package verification complete")
