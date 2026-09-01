#!/usr/bin/env python3
"""Conan consumer test for aevol 9.4.0."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AevolTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_aevol.py", "param.in"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["aevol"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        create = os.path.join(bin_dir, "aevol_create_2b")
        if not os.path.isfile(create):
            raise AssertionError(f"Missing aevol_create_2b executable: {create}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_aevol.py")
        param = os.path.join(self.source_folder, "param.in")
        result = self.run(
            f'"{sys.executable}" "{script}" "{bin_dir}" "{param}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(f"aevol smoke test failed with exit code {result}")
