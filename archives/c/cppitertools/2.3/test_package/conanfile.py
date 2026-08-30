#!/usr/bin/env python3
"""Conan test_package — cppitertools header-only consumer test (L1).

Compiles and runs a consumer binary that exercises the installed headers
(range, enumerate, zip) to prove the package is usable end-to-end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CppIterToolsTestConan(ConanFile):
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
        # Fallback: run the test binary directly with conanrun env
        if not self.cpp.build.bindirs:
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_cppitertools"), env="conanrun")