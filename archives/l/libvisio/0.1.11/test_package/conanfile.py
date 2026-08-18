#!/usr/bin/env python3
"""Conan test_package for libvisio 0.1.11.

L1 test: verifies the library can be linked and its API called.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibvisioTestConan(ConanFile):
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
        # L0d: test() must include self.run()
        cmake = CMake(self)
        cmake.test()
        # Also run the binary directly to satisfy R34
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libvisio")
        self.run(bin_path, env="conanrun")
