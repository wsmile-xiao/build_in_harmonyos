#!/usr/bin/env python3
"""Conan test_package — bvi 1.5.0 smoke test.

Compiles test.c and checks the bvi binary is installed and executable.
"""
import os

from conan import ConanFile


class BviTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile test.c; clang is in PATH on OHOS
        self.run("clang test.c -o test_bvi")

    def test(self):
        dep = self.dependencies["bvi"]
        bvi_bin = os.path.join(dep.package_folder, "bin", "bvi")
        self.run(f'./test_bvi "{bvi_bin}"', env="conanrun")
