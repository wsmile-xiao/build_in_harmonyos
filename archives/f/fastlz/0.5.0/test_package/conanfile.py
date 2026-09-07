#!/usr/bin/env python3
"""Conan test_package — fastlz 0.5.0 L1 test.

R34: test calls fastlz API (fastlz_compress / fastlz_decompress round-trip).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FastlzTestConan(ConanFile):
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
        # R34: run the test binary that calls fastlz API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_fastlz")
        self.run(test_bin, env="conanrun")