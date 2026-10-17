#!/usr/bin/env python3
"""Conan test_package for py-cpuinfo 9.0.0 — import + API + CLI tests."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PyCpuinfoTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            test_script = os.path.join(os.path.dirname(__file__), "test_cpuinfo.py")
            self.run(f'{python_exe} "{test_script}"', env="conanrun")
