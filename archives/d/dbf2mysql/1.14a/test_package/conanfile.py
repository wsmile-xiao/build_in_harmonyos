#!/usr/bin/env python3
"""Conan test package for the dbf2mysql 1.14a Makefile application."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class Dbf2mysqlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Target executables cannot run with the current profile")
            return

        dependency = self.dependencies["dbf2mysql"]
        dbf2mysql = os.path.join(dependency.package_folder, "bin", "dbf2mysql")
        mysql2dbf = os.path.join(dependency.package_folder, "bin", "mysql2dbf")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'"{bash}" "{script}" "{dbf2mysql}" "{mysql2dbf}"',
            env="conanrun",
        )
