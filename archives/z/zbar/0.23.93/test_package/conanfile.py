#!/usr/bin/env python3
"""Conan test_package — zbar 0.23.93

Tests that libzbar can be linked and the scanner API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZbarTestConan(ConanFile):
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
        # Also run test_zbar directly to verify runtime linkage
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_zbar")
        self.run(f"{bin_path}", env="conanrun")
