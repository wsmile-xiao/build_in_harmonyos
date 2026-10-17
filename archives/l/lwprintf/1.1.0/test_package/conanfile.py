#!/usr/bin/env python3
"""Conan test_package — lwprintf 1.1.0 consumer test (L1, PF3).

The consumer program calls the public lwprintf API (lwprintf_snprintf) and
verifies observable output; the test() method actually runs the binary
via self.run (L0d requires a real self.run execution path).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LwprintfTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lwprintf")
        self.run(test_bin, env="conanrun")
