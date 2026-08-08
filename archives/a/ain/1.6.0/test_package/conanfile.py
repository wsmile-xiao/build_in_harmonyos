#!/usr/bin/env python3
"""Conan test_package for ain 1.6.0 (Go CLI)."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class AinTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ain"].package_folder
        exe_name = "ain.exe" if str(self.settings.os) == "Windows" else "ain"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"ain binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{bin_path}"', env="conanrun")
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"ain is not an ELF binary: {magic!r}"
            self.output.info(f"ain binary exists and has ELF magic: {bin_path}")
