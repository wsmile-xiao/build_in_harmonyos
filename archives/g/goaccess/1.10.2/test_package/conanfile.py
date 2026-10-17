#!/usr/bin/env python3
"""Conan test_package — goaccess 1.10.2.

Verifies that the goaccess binary is correctly built and can report its
version. This is the L1 (smoke) test in the CI test hierarchy.

R34: test must exercise the actual built binary, not just print a string.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GoaccessTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # R34: Exercise the actual goaccess binary
        bin_path = os.path.join(self.dependencies["goaccess"].package_folder, "bin", "goaccess")
        self.run(f'"{bin_path}" --version', env="conanrun")
