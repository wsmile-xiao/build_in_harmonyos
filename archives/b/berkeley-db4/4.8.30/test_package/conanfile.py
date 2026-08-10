#!/usr/bin/env python3
"""Conan test_package for berkeley-db4 4.8.30.

Tests Berkeley DB API: create, open, put, get, close.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Berkeleydb4TestConan(ConanFile):
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
        # Run the test binary directly to verify the library API works
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_berkeley_db4")
        self.run(bin_path, env="conanrun")
