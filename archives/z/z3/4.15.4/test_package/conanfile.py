#!/usr/bin/env python3
"""Conan test_package for z3/4.15.4 — verifies the z3 C API is functional.

This test creates an SMT context, declares an integer constant x,
asserts x > 100, and checks satisfiability. Expected result: sat.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Z3TestConan(ConanFile):
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
        # Run the test binary that uses z3 C API to verify the library
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_z3")
        self.run(test_bin, env="conanrun")
