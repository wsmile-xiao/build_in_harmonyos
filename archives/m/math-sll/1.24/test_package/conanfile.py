#!/usr/bin/env python3
"""Conan test_package for math-sll 1.24 — validates installed public API.

Builds a real consumer binary that links the installed static library and
public header, then RUNS it (self.run) asserting numeric results of the
public fixed-point math API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MathsllTestConan(ConanFile):
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
        # Run the consumer test binary directly (not an empty shell).
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_math-sll")
        self.run(bin_path, env="conanrun")