#!/usr/bin/env python3
"""Conan test_package — jsonnet C API consumer test.

Tests that the jsonnet library can be linked and used to evaluate
a simple Jsonnet expression via the C API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JsonnetTestConan(ConanFile):
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
        # Run the test binary directly instead of cmake.test()
        # CTest outputs "0 tests failed" which can trigger false-positive
        # "test_package: failed" detection in CI log parsing.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_jsonnet"), env="conanrun")
