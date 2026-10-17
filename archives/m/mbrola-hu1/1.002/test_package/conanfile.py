#!/usr/bin/env python3
"""Semantic consumer tests for the MBROLA HU1 voice database."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class MbrolaHu1TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_root = self.dependencies["mbrola-hu1"].package_folder
        script = os.path.join(
            self.source_folder,
            "test_mbrola_hu1.py",
        )
        command = (
            f'"{sys.executable}" "{script}" '
            f'--package-root "{package_root}"'
        )
        self.run(command, env="conanrun")
