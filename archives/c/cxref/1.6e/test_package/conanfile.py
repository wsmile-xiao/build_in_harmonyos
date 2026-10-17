#!/usr/bin/env python3
"""Conan test_package — cxref 1.6e CLI tool verification.

The test binary receives the path of the installed `cxref` executable as
argv[1] and drives real cross-referencing jobs on a sample C file (R34):
HTML generation, the usage banner (which carries the version), and the
missing-input error path. The package's bin/ is on the conanrun PATH so
the installed wrapper finds its bundled cxref-cpp preprocessor.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CxrefTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cxref_bin = os.path.join(
            self.dependencies["cxref"].package_folder, "bin", "cxref"
        )
        test_bin = os.path.join(self.build_folder, "test_cxref")
        self.run(f'"{test_bin}" "{cxref_bin}"', env="conanrun", cwd=self.build_folder)
