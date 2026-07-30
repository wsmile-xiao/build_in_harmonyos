#!/usr/bin/env python3
"""Conan test_package for libudev-zero — L1 official test.

Verifies that the libudev-zero package provides a functional libudev API
by creating a udev context, ref/unref, and checking API availability.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibudevZeroTestConan(ConanFile):
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
        # Explicitly run the test binary for L0d gate verification
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libudev-zero")
        self.run(test_bin, env="conanrun")
