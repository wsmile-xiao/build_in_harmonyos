#!/usr/bin/env python3
"""Conan test_package — libngtcp2 1.22.1

Verifies that the libngtcp2 package provides a working ngtcp2 library
by calling ngtcp2_version() and checking the returned version string.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libngtcp2TestConan(ConanFile):
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
        # R34: test must genuinely depend on the package
        # Calls ngtcp2_version() to verify the library is linked and functional
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libngtcp2")
        self.run(test_bin, env="conanrun")
