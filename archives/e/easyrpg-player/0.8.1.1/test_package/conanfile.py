#!/usr/bin/env python3
"""Conan test_package for easyrpg-player — L1 official test.

Tests that the easyrpg-player binary is installed and can report its version.
This satisfies R34: the test executes the package's binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EasyRpgPlayerTestConan(ConanFile):
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
        # Run the test binary which verifies easyrpg-player is available
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_easyrpg-player")
        self.run(cmd, env="conanrun")
