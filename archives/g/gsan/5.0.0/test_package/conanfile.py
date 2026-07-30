#!/usr/bin/env python3
"""Test package for gsan 5.0.0."""
import sys
from conan import ConanFile
from conan.tools.build import can_run


class GsanTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run(f'"{sys.executable}" test_gsan.py', env="conanrun")