#!/usr/bin/env python3
"""Conan test_package for libimobiledevice-glue — verifies the SHA-256 API.

Computes SHA-256 of "abc" and verifies the result against the known
FIPS 180-2 test vector, confirming the library functions correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibimobiledeviceGlueTestConan(ConanFile):
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
        # Run the test binary directly (CI L0e requires self.run())
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libimobiledevice_glue")
        self.run(bin_path, env="conanrun")
