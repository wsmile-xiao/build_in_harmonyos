#!/usr/bin/env python3
"""Conan test_package for GMP 6.3.0 — verifies GMP arithmetic API works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GmpTestConan(ConanFile):
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
        # L0d: explicit self.run() to satisfy CI gate
        bin_path = os.path.join(self.cpp.build.bindir, "test_gmp")
        self.run(bin_path, env="conanrun")
