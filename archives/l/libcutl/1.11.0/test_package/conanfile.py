#!/usr/bin/env python3
"""Conan test_package — libcutl 1.11.0 (L1 smoke test)

Verifies that libcutl's fs::path, exception, and compiler::type_id
APIs are functional after Conan package installation.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibcutlTestConan(ConanFile):
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
        # Run the test binary directly to verify libcutl API calls
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libcutl"), env="conanrun")
