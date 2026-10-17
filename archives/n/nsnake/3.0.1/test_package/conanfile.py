#!/usr/bin/env python3
"""Conan test_package — nsnake 3.0.1.

Since nsnake is a terminal game (ncurses-based), we can't run it
interactively in CI.  Instead we verify the binary is present and
executable by dumping --version output.
"""
import os
from conan import ConanFile


class NsnakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the binary is installed and responds to --version
        bin_path = os.path.join(self.dependencies["nsnake"].package_folder,
                                "bin", "nsnake")
        self.output.info(f"Checking binary: {bin_path}")
        self.run(f"{bin_path} --version", env="conanrun")