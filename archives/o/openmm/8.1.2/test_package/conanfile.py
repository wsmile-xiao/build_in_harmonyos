#!/usr/bin/env python3
"""Conan test_package for OpenMM 8.1.2 — verifies the library is functional.

Test: creates a simple molecular system, adds a particle, and verifies
the OpenMM version string matches the expected release.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenmmTestConan(ConanFile):
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
        # Run the test binary directly for L0d compliance and functional verification
        self.run(os.path.join(self.cpp.build.bindir, "test_openmm"), env="conanrun")
