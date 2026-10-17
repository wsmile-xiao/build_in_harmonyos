#!/usr/bin/env python3
"""Conan test_package for directx-headers 1.619.1"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DirectXHeadersTestConan(ConanFile):
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
        # Also run the test binary directly to verify the package
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_directx_headers"), env="conanrun")
