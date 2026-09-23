#!/usr/bin/env python3
"""Conan test_package for mifluz/0.26.0 — consumer test (L1).

Builds test.cpp against the packaged libmifluz and runs the consumer
binary; the binary builds an inverted index, inserts a reference and
searches it back via the real libmifluz API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MifluzTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mifluz")
        self.run(test_bin, env="conanrun")
