#!/usr/bin/env python3
"""Conan test_package for pastebinit 1.8.0 — Conan L1 smoke test.

Verifies the installed pastebinit binary can display help, report version,
and list supported pastebins.
"""
import os

from conan import ConanFile


class PastebinitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(
            self.dependencies["pastebinit"].package_folder, "bin", "pastebinit"
        )
        assert os.path.isfile(bin_path), f"pastebinit binary not found: {bin_path}"

        test_script = os.path.join(self.recipe_folder, "test_pastebinit.sh")
        self.run(f'sh "{test_script}" "{bin_path}"', env="conanrun")
