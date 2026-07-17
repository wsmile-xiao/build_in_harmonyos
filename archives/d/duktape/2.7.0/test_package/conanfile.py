#!/usr/bin/env python3
"""Conan test_package for duktape 2.7.0.

Verifies that the duktape library is properly built and the C API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DuktapeTestConan(ConanFile):
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
        # R34: Run the test binary directly to verify the duktape C API
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_duktape"), env="conanrun")
