#!/usr/bin/env python3
"""Conan test_package — Octave 8.3.0 L1 smoke test.

Verifies that octave-cli is functional by running --version
and a basic numerical computation.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OctaveTestConan(ConanFile):
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
        # Run the test binary
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_octave')}", env="conanrun")
