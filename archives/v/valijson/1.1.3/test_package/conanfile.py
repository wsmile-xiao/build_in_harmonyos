#!/usr/bin/env python3
"""Conan test_package — valijson 1.1.3 (CMake header-only library).

L1 test: compile a small C++ program that includes valijson headers,
builds a schema programmatically, and performs real validation through
the public API (R34: not an empty-shell test).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ValijsonTestConan(ConanFile):
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
        # Run the test binary — exits 0 on success
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_valijson"), env="conanrun")