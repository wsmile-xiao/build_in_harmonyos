#!/usr/bin/env python3
"""Conan test_package — pkill 4.0.6

pkill is a binary tool (not a library). The test verifies:
1. The package can be consumed (L1 compile test)
2. The pkill binary exists and responds to --version
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PkillTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "PKILL_BIN": os.path.join(
                self.dependencies["pkill"].package_folder, "bin", "pkill")})
        cmake.build()

    def test(self):
        # L1: Run the compile test
        cmake = CMake(self)
        cmake.test()

        # R34: Unconditionally run the pkill binary — test must depend on the package.
        # If the binary is missing (e.g., L1e sabotage), this will fail.
        bin_path = os.path.join(self.dependencies["pkill"].package_folder, "bin", "pkill")
        self.run(f'"{bin_path}" -V', env="conanrun")
