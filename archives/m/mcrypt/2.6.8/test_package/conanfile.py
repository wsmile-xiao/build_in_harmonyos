#!/usr/bin/env python3
"""Conan test_package for mcrypt 2.6.8."""
import sys
from pathlib import Path

from conan import ConanFile


class McryptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe = Path(self.dependencies["mcrypt"].package_folder) / "bin" / "mcrypt"
        if not exe.is_file():
            raise RuntimeError(f"missing mcrypt executable: {exe}")
        script = Path(self.recipe_folder) / "test_mcrypt.py"
        self.run(f'"{sys.executable}" "{script}" "{exe}"', env="conanrun")
