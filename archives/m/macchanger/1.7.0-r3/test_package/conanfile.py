#!/usr/bin/env python3
"""Conan test_package for macchanger — L1 smoke test.

Runs the installed macchanger binary with --version
to verify the package is functional.
"""
import os

from conan import ConanFile


class MacchangerTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["macchanger"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged binary with a real smoke test
        self.run(f"sh test_macchanger.sh {bin_dir}", env="conanrun")
        self.output.info("macchanger: OK")
