#!/usr/bin/env python3
"""Test script for arduino-mk 1.6.0 Conan package.

This script verifies that the package correctly installs:
1. .mk include files in share/arduino/
2. Python utility scripts in bin/
3. Man pages in share/man/man1/

Called by test_package/conanfile.py test() method.
"""
import os
import sys


def test_package_contents(package_root):
    """Verify all expected files are installed and contain valid content."""
    errors = []

    # 1. Verify .mk files in share/arduino/
    arduino_dir = os.path.join(package_root, "share", "arduino")
    expected_mk_files = [
        "Arduino.mk", "Common.mk", "OpenCM.mk",
        "Teensy.mk", "chipKIT.mk", "arduino-mk-vars.md"
    ]
    for f in expected_mk_files:
        fpath = os.path.join(arduino_dir, f)
        if not os.path.isfile(fpath):
            errors.append(f"Missing installed file: {fpath}")
        elif os.path.getsize(fpath) == 0:
            errors.append(f"Empty file: {fpath}")

    # 2. Verify Arduino.mk content (substantive check per R34)
    arduino_mk_path = os.path.join(arduino_dir, "Arduino.mk")
    if os.path.isfile(arduino_mk_path):
        with open(arduino_mk_path, "r") as fh:
            content = fh.read()
            if "ARDUINO" not in content:
                errors.append("Arduino.mk does not contain ARDUINO variable")
            if "ARDMK" not in content:
                errors.append("Arduino.mk does not contain ARDMK variable")

    # 3. Verify executables in bin/
    bin_dir = os.path.join(package_root, "bin")
    expected_bin_files = ["ard-reset-arduino", "robotis-loader"]
    for f in expected_bin_files:
        fpath = os.path.join(bin_dir, f)
        if not os.path.isfile(fpath):
            errors.append(f"Missing executable: {fpath}")

    # 4. Verify ard-reset-arduino is a valid Python script (R34)
    ard_reset_path = os.path.join(bin_dir, "ard-reset-arduino")
    if os.path.isfile(ard_reset_path):
        with open(ard_reset_path, "r") as fh:
            first_line = fh.readline()
            if "python" not in first_line:
                errors.append(f"ard-reset-arduino is not a Python script: {first_line}")
            content = fh.read()
            if "serial" not in content:
                errors.append("ard-reset-arduino does not use serial module")

    # 5. Verify man pages
    man_dir = os.path.join(package_root, "share", "man", "man1")
    expected_man_files = ["ard-reset-arduino.1", "robotis-loader.1"]
    for f in expected_man_files:
        fpath = os.path.join(man_dir, f)
        if not os.path.isfile(fpath):
            errors.append(f"Missing man page: {fpath}")

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: test_arduino_mk.py <package_root>")
        sys.exit(1)

    package_root = sys.argv[1]
    errors = test_package_contents(package_root)

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    else:
        print("All arduino-mk package tests passed!")
        sys.exit(0)
