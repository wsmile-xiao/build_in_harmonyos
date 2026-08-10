#!/usr/bin/env python3
"""Conan test_package for libplist — verifies the C API works.

Creates a simple plist, adds a key/value, serializes to XML, and
deserializes back to verify the library functions correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibplistTestConan(ConanFile):
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
        # Run the test binary directly (CI L0e requires self.run())
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libplist")
        self.run(bin_path, env="conanrun")
