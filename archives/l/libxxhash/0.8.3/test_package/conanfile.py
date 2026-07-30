#!/usr/bin/env python3
"""Conan test_package — libxxhash 0.8.3.

Tests the xxHash API: XXH64 one-shot, streaming, XXH32, seed variation.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxxhashTestConan(ConanFile):
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
        # Also run the binary directly to satisfy L0d (R34: substantive test)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libxxhash")
        self.run(test_bin, env="conanrun")
