#!/usr/bin/env python3
"""Conan consumer tests for libfixmath 0-20220222."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfixmathTestConan(ConanFile):
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
            "ctest --test-dir . --output-on-failure --no-tests=error",
            cwd=self.build_folder,
            env="conanrun",
        )
