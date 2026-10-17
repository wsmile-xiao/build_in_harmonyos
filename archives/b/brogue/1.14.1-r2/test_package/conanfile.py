#!/usr/bin/env python3
"""Conan test_package — brogue 1.14.1-r2."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BrogueTestConan(ConanFile):
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
        # Alternatively, run the binary directly:
        # self.run("./test_brogue", env="conanrun")
