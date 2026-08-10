#!/usr/bin/env python3
"""Conan test_package for odbc-cpp-wrapper 1.6."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OdbcCppWrapperTestConan(ConanFile):
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
        # Also run the binary directly to verify library linkage
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_odbccpp"), env="conanrun")
