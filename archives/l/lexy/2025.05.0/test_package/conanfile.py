#!/usr/bin/env python3
"""Conan test_package for lexy — Conan L1 official test.

Compiles test_lexy.cpp against the lexy parser combinator library (headers
from include/lexy) and runs it to verify the DSL-based parser actually
parses input. Uses Conan's CMakeToolchain for cross-compilation support.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LexyTestConan(ConanFile):
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
        test_bin = os.path.join(self.build_folder, "test_lexy")
        self.run(test_bin, env="conanrun")
