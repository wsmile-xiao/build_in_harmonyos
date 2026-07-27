#!/usr/bin/env python3
"""Conan test_package — tbb 2023.0.0 (oneTBB shared library).

L1 test: compile a C++ program that uses tbb::parallel_for
to verify the library is linkable and functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TbbTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tbb"), env="conanrun")
