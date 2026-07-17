#!/usr/bin/env python3
"""Test package for SIPp 3.7.7."""

from conan import ConanFile
from conan.tools.build import can_run


class SippTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("sipp -v", env="conanrun")
