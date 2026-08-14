#!/usr/bin/env python3
"""Conan test_package for gsoap 2.8.142.

L1 consumer test: links against libgsoap.a and exercises the gsoap API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GsoapTestConan(ConanFile):
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
        # Run the test binary directly to verify gsoap API works
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_gsoap"), env="conanrun")
