#!/usr/bin/env python3
"""Conan test_package — libtar L1 consumer test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtarTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libtar")
        lib_dir = os.path.join(self.dependencies["libtar"].package_folder, "lib")
        self.run(f'LD_LIBRARY_PATH="{lib_dir}" {bin_path}')
