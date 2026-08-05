#!/usr/bin/env python3
"""Conan test_package for wego 2.4 — consumer smoke test.

wego is a Go CLI application (not a linkable C/C++ library). The consumer test
runs the packaged `wego` binary with `-h` and asserts:
  - exit code 0
  - stdout mentions all stable frontend/backend keywords

File location: archives/w/wego/2.4/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class WegoTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["wego"].package_folder
        exe_name = "wego.exe" if str(self.settings.os) == "Windows" else "wego"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"wego binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{test_script}" "{bin_path}"', env="conanrun")
        else:
            # Cross-compile host: validate ELF magic only (cannot execute target binary).
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"wego is not an ELF binary: {magic!r}"
            self.output.info(f"wego binary exists and has ELF magic: {bin_path}")
