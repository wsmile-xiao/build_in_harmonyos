#!/usr/bin/env python3
"""Conan test_package for dmidecode 3.6 — L1 smoke test.

dmidecode is a command-line tool, not a library.
The L1 test verifies the binary runs and reports the correct version.
"""
import os

from conan import ConanFile


class DmidecodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step — testing the prebuilt binary

    def test(self):
        # L2 smoke test: run dmidecode --version via test.sh
        dep = self.dependencies["dmidecode"]
        bin_path = os.path.join(dep.package_folder, "bin", "dmidecode")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{bin_path}"')
