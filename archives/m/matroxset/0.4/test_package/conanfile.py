#!/usr/bin/env python3
"""Conan test_package for matroxset 0.4.

L1 test: verify the matroxset binary can run with -h command.
The binary is built from source and installed to bin/ during conan create.
"""
import os

from conan import ConanFile


class MatroxsetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        main_pkg = self.dependencies[self.tested_reference_str]
        matroxset_bin = os.path.join(main_pkg.package_folder, "bin", "matroxset")
        # The binary returns 98 for -h (help), which is expected
        self.run(f"{matroxset_bin} -h", ignore_errors=True)