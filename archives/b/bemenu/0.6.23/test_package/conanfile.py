#!/usr/bin/env python3
"""Conan test_package for bemenu 0.6.23 — L1 test.

Tests that libbemenu can be linked and bm_version() returns the
expected version string.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BemenuTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_bemenu")
        # Set LD_LIBRARY_PATH directly in command for OHOS/musl compatibility
        lib_dir = os.path.join(self.dependencies["bemenu"].package_folder, "lib")
        self.run(f'LD_LIBRARY_PATH="{lib_dir}" "{bin_path}"')
