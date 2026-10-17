#!/usr/bin/env python3
"""Conan consumer test for yyjson 0.13.0."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YyjsonTestConan(ConanFile):
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
        self.run(
            f'ctest --test-dir "{self.build_folder}" '
            "--output-on-failure --no-tests=error",
            env="conanrun",
        )