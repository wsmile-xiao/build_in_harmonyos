#!/usr/bin/env python3
"""Conan test_package for ktx-software — verifies libktx API is callable.

L1 test: calls ktxTexture_CreateFromMemory() with invalid data and verifies
the library returns a proper error code (not KTX_SUCCESS).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KtxSoftwareTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ktx"), env="conanrun")
