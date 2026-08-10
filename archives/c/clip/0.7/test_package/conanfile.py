#!/usr/bin/env python3
"""Conan test_package for clip — verifies the clip C API is functional.

This test creates a clip context, verifies it is non-NULL, and destroys it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ClipTestConan(ConanFile):
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
        # R34: Run the test binary directly to verify the clip C API
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_clip"), env="conanrun")
