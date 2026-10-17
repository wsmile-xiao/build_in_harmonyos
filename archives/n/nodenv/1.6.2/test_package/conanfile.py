#!/usr/bin/env python3
"""Test package for nodenv — smoke test via test_nodenv.sh."""
import os

from conan import ConanFile


class NodenvTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["nodenv"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged nodenv script — verify presence,
        # executable bit, shebang, bash syntax, and --version output.
        self.run(f"bash test_nodenv.sh {bin_dir}", env="conanrun")
        self.output.info("nodenv: OK")
