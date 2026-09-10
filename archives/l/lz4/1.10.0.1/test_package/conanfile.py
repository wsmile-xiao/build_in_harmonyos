#!/usr/bin/env python3
"""Conan test_package — lz4 1.10.0 L1 test.

R34: test calls lz4 API (LZ4_compress_default / LZ4_decompress_safe).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Lz4TestConan(ConanFile):
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
        # R34: run the test binary that calls lz4 API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lz4")
        self.run(test_bin, env="conanrun")
