#!/usr/bin/env python3
"""Conan test_package — concalc CLI behaviour verification.

concalc is a CLI tool, so the test binary receives the path of the installed
executable and asserts real calculator behaviour (R34): version banner and
expression evaluation including function calls.
"""
import os

from conan import ConanFile


class ConcalcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} -O2 -std=gnu99 test.c -o test_probe")

    def test(self):
        concalc_bin = os.path.join(
            self.dependencies["concalc"].package_folder, "bin", "concalc"
        )
        self.run(f'./test_probe "{concalc_bin}"', env="conanrun")
