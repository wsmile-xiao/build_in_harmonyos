#!/usr/bin/env python3
"""Conan test_package for blend2d 0.21.2.

Verifies that the library can be linked and that basic rendering operations
(image creation, context, fill rectangle) work correctly by checking pixel
data output.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Blend2DTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        self.run("ctest --output-on-failure", env="conanrun")
