#!/usr/bin/env python3
"""Conan test_package — libdecaf 1.0.2 consumer test.

Tests the decaf_448 C API (scalar arithmetic, point arithmetic,
encode/decode round trip, validity, identity handling) by linking
against the packaged library.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdecafTestConan(ConanFile):
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
        # Run the test binary directly to verify the library API works
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdecaf")
        self.run(test_bin, env="conanrun")
