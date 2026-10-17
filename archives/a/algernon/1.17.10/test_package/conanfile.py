#!/usr/bin/env python3
"""Conan consumer test for algernon 1.17.10."""

import os
import subprocess
import sys
import urllib.request

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AlgernonTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_algernon.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["algernon"].package_folder
        exe = os.path.join(package_folder, "bin", "algernon")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing algernon executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_algernon.py")
        result = self.run(
            f'"{sys.executable}" "{script}" "{exe}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(f"algernon smoke test failed with exit code {result}")
