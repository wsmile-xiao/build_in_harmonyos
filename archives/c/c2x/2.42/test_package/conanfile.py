#!/usr/bin/env python3
"""Conan test_package for c2x 2.42 — Conan L1 official test.

c2x is a CLI tool, so the test runs the produced binary directly and
asserts real behaviour:
  1. Binary exists
  2. -h prints usage
  3. no-args fails gracefully with a message
  4. -V reports version and the no-SPGLIB build configuration
  5. CASTEP .cell -> XSF conversion produces a valid XSF file
"""
import os

from conan import ConanFile


class C2xTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        c2x = os.path.join(
            self.dependencies["c2x"].cpp_info.bindirs[0],
            "c2x",
        )
        test_script = os.path.join(self.source_folder, "test_c2x.py")
        self.run(f'python3 "{test_script}" "{c2x}"', env="conanrun")
