#!/usr/bin/env python3
"""Conan test_package — vtzero 1.2.0 (header-only C++ library).

L1 test: compile a small C++ program that includes vtzero headers
(vector_tile.hpp) and builds a minimal vector tile decode/encode round-trip.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VtzeroTestConan(ConanFile):
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
        # Run the test binary — exits 0 on success
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_vtzero"), env="conanrun")
