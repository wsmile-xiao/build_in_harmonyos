#!/usr/bin/env python3
"""Conan test_package for openjpeg — verifies the library is usable.

This test exercises the openjpeg API by:
1. Calling opj_version() to verify the library is linked correctly
2. Creating a decompressor handle to verify API availability
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenjpegTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
        # Run the test binary directly to verify API linkage
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_openjpeg')}", env="conanrun")
