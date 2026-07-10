#!/usr/bin/env python3
"""Conan test_package for internetarchive 5.10.1 — Python import test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class InternetarchiveTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            test_script = os.path.join(os.path.dirname(__file__), "test_ia.py")
            self.run(f'{python_exe} "{test_script}"', env="conanrun")
