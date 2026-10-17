#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for fixed_string.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FixedStringTestConan(ConanFile):
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
        # Direct binary invocation (L0d requires an actual self.run() call):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_fixed_string"), env="conanrun")
