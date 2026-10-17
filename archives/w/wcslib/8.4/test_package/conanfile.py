#!/usr/bin/env python3
"""Conan test_package for wcslib 8.4.

Builds a test program that calls the WCSLIB prj (projection) API:
  prjini() -> prjset() -> prjx2s() -> prjs2x() -> verify closure.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WcslibTestConan(ConanFile):
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
        # Run the test executable directly via self.run() so the L0d gate
        # detects an actual test invocation (cmake.test() is not recognized).
        # env="conanrun" uses Conan's generated runtime environment (standard
        # for Conan 2); the library is static so no LD_LIBRARY_PATH is needed.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_wcslib")
        self.run(exe, env="conanrun")
