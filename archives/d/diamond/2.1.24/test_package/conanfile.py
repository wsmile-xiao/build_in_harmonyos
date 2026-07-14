#!/usr/bin/env python3
"""Conan test_package — diamond CLI tool test.

diamond is a command-line tool, not a library. Test by running the binary.
test.sh is the source file for CI L0c compliance.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class DiamondTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["diamond"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            diamond = os.path.join(bin_dir, "diamond")

            # R34: substantive test — execute the diamond binary
            self.run(f"{diamond} --version", env="conanrun")
            self.run(f"{diamond} test", env="conanrun")