#!/usr/bin/env python3
"""Conan test_package — reaver 1.6.6

L1 test: verify the reaver and wash binaries are installed and functional.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ReaverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg_folder = self.dependencies["reaver"].package_folder
            bin_dir = os.path.join(pkg_folder, "bin")
            script_path = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{script_path}" "{bin_dir}"', env="conanrun")