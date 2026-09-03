#!/usr/bin/env python3
"""Conan test_package for pystring 1.1.4.

This tests the pystring library by calling its API functions:
  - pystring::split
  - pystring::join
  - pystring::strip
  - pystring::upper
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PystringTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_pystring"), env="conanrun")
