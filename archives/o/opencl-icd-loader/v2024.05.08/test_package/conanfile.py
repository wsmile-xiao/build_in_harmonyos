#!/usr/bin/env python3
"""Conan test_package — opencl-icd-loader v2024.05.08

L1 test: calls clGetPlatformIDs to verify the ICD loader library is
correctly built and linkable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenclIcdLoaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("opencl-headers/2026.05.29")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_opencl_icd_loader"), env="conanrun")
