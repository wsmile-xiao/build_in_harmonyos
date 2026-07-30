#!/usr/bin/env python3
"""Conan test_package for jitterentropy-library 3.6.3.

Tests the jitterentropy API: init, alloc, read_entropy, free.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JitterentropyLibraryTestConan(ConanFile):
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
        # Run the test binary directly to satisfy L0d gate (requires self.run())
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_jitterentropy")
        self.run(test_bin, env="conanrun")
