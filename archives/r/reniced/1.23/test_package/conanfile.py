#!/usr/bin/env python3
"""Conan test_package for reniced 1.23."""
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class RenicedTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        package_folder = Path(self.dependencies["reniced"].package_folder)
        perl = Path(self.dependencies["perl"].package_folder) / "bin" / "perl"
        checker = Path(self.source_folder) / "test_reniced.py"

        for path in (
            package_folder / "bin" / "reniced",
            package_folder / "share" / "reniced" / "reniced.conf",
            package_folder / "share" / "doc" / "reniced" / "README.md",
            package_folder / "licenses" / "COPYRIGHT",
        ):
            if not path.is_file():
                raise RuntimeError(f"missing packaged reniced artifact: {path}")

        if not can_run(self):
            self.output.info("Cross-building; reniced layout check completed")
            return

        self.run(
            f'"{sys.executable}" "{checker}" "{package_folder}" "{perl}"',
            env="conanrun",
        )
