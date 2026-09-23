#!/usr/bin/env python3
"""Conan test_package for buckygen 1.1 — Conan L1 official test.

buckygen is a CLI tool (fullerene generator), so the test runs the binary
directly.  The test verifies:
  1. Binary exists and is executable
  2. Running without args shows usage information
  3. Generation works: `buckygen 24 -u` counts fullerenes with 24 vertices
  4. Count output format contains the expected counter line
"""
import os

from conan import ConanFile


class BuckygenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        buckygen = os.path.join(
            self.dependencies["buckygen"].cpp_info.bindirs[0],
            "buckygen",
        )
        test_script = os.path.join(self.source_folder, "test_buckygen.py")
        self.run(f'python3 "{test_script}" "{buckygen}"', env="conanrun")
