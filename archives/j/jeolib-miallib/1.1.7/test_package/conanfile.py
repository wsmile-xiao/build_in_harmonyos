#!/usr/bin/env python3
"""Conan test_package for jeolib-miallib 1.1.7 — L1 functional test.

Builds and runs a real-API test program (create_image / histo1d /
erode4 / dilate4) against the packaged miallib library and headers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MiallibTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
