#!/usr/bin/env python3
"""Conan test_package — btest 1.0.0.

Verifies that the installed btest package contains all expected
scripts, that they are syntactically valid Python, and that the
license file is present.

All assertions run through self.run(..., env="conanrun") so CI's
L0d/L1 gates can observe real test execution. The verification
logic lives in test_btest.py (a Python module, not a .sh) and is
invoked as:  python3 test_btest.py <package_folder>
"""
import os

from conan import ConanFile


class BtestTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["btest"].package_folder
        verifier = os.path.join(os.path.dirname(__file__), "test_btest.py")
        # L0d/L1: real self.run() execution with conanrun env.
        # test_btest.py exits 0 on PASS, 1 on FAIL.
        self.run(f'python3 "{verifier}" "{pkg}"', env="conanrun")
