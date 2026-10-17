#!/usr/bin/env python3
"""Conan test_package — arduino-mk 1.6.0

Verifies that the package correctly installs:
- .mk include files (Arduino.mk, Common.mk, etc.) in share/arduino/
- Python utility scripts (ard-reset-arduino, robotis-loader) in bin/
- Man pages in share/man/man1/

This test substantively depends on the tested package (R34):
it reads and validates content of installed .mk files and scripts.
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class ArduinomkTestConan(ConanFile):
    settings = "os"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        # No build step needed — we validate installed files
        pass

    def test(self):
        # R34: Substantively verify the installed package contents
        # Get the package root folder via the dependency
        dep = self.dependencies["arduino-mk"]
        package_root = dep.package_folder

        # Run the test script that checks all installed files
        test_script = os.path.join(os.path.dirname(__file__), "test_arduino_mk.py")
        self.run(f"{sys.executable} {test_script} {package_root}", env="conanrun")
        self.output.info("All arduino-mk package tests passed!")
