#!/usr/bin/env python3
"""Conan test_package — addrwatch 1.0.2

L1 test: verify the addrwatch binary is installed and can show help.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AddrwatchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the addrwatch binary in the package folder
        pkg_folder = self.dependencies["addrwatch"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "addrwatch")
        if can_run(self):
            self.run(f'"{bin_path}" --help', env="conanrun")
