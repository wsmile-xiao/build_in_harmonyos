#!/usr/bin/env python3
"""Test package for nvm — smoke test via test_nvm.sh."""
import os

from conan import ConanFile


class NvmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["nvm"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged nvm script — verify presence,
        # executable bit, shebang, bash syntax, and --version output.
        self.run(f"bash test_nvm.sh {bin_dir}", env="conanrun")
        self.output.info("nvm: OK")
