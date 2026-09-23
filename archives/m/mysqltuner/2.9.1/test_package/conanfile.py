#!/usr/bin/env python3
"""Conan test_package for mysqltuner 2.9.1."""
import os
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class MysqltunerTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        package_folder = Path(self.dependencies["mysqltuner"].package_folder)
        perl = Path(self.dependencies["perl"].package_folder) / "bin" / "perl"
        checker = Path(self.source_folder) / "test_mysqltuner.py"

        for path in (
            package_folder / "bin" / "mysqltuner",
            package_folder / "bin" / "mysqltuner.pl",
            package_folder / "share" / "mysqltuner" / "basic_passwords.txt",
            package_folder / "share" / "mysqltuner" / "vulnerabilities.csv",
            package_folder / "licenses" / "LICENSE",
        ):
            if not path.is_file():
                raise RuntimeError(f"missing packaged mysqltuner artifact: {path}")

        if not can_run(self):
            self.output.info("Cross-building; mysqltuner layout check completed")
            return

        self.run(
            f'"{sys.executable}" "{checker}" "{package_folder}" "{perl}"',
            env="conanrun",
        )
