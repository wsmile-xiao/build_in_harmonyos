#!/usr/bin/env python3
"""Conan test_package — trompeloeil 49 consumer test.

Builds and runs a Catch2-driven consumer that includes the packaged header,
defines mocks, sets expectations and asserts real return values plus
violation reporting.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TrompeloeilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("catch2/3.8.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_trompeloeil")
        self.run(binary, env="conanrun")
