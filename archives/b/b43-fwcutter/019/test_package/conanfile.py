#!/usr/bin/env python3
"""Conan test_package for b43-fwcutter 019 — Conan L1 official test.

b43-fwcutter is a CLI tool, so the test runs the binary directly.
The test verifies:
  1. Binary exists and is executable
  2. Running without args shows usage information
  3. Running with -l lists supported driver files
  4. Version string contains 019
"""
import os

from conan import ConanFile


class B43FwcutterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        fwcutter = os.path.join(
            self.dependencies["b43-fwcutter"].cpp_info.bindirs[0],
            "b43-fwcutter",
        )
        test_script = os.path.join(self.source_folder, "test_b43_fwcutter.py")
        self.run(f'python3 "{test_script}" "{fwcutter}"', env="conanrun")
