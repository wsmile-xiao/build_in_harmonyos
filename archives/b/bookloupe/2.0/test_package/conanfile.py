#!/usr/bin/env python3
"""Conan test_package for bookloupe 2.0."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BookloupeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        bookloupe = os.path.join(
            self.dependencies["bookloupe"].package_folder, "bin", "bookloupe")
        script = os.path.join(self.source_folder, "test_bookloupe.sh")
        bash = (os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
                or "/data/service/hnp/bin/bash")
        self.run(f'BOOKLOUPE_BIN="{bookloupe}" "{bash}" "{script}"',
                 env="conanrun")
