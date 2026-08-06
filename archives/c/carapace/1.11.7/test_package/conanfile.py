#!/usr/bin/env python3
"""Conan test_package for carapace 1.11.7."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class CarapaceTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["carapace"].package_folder
        for exe_name in ("example", "example-nonposix"):
            bin_path = os.path.join(package_folder, "bin", exe_name)
            assert os.path.isfile(bin_path), f"carapace binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{package_folder}"', env="conanrun")
        else:
            for exe_name in ("example", "example-nonposix"):
                bin_path = os.path.join(package_folder, "bin", exe_name)
                with open(bin_path, "rb") as binary:
                    magic = binary.read(4)
                assert magic == b"\x7fELF", f"{exe_name} is not an ELF binary: {magic!r}"
                self.output.info(f"{exe_name} binary exists and has ELF magic: {bin_path}")
