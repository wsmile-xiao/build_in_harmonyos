#!/usr/bin/env python3
"""Conan test_package for umka-lang 1.5.5.

This test calls the Umka C embedding API:
- umkaGetVersion() to verify the library is loaded
- umkaAlloc/umkaInit/umkaCompile/umkaRun to run a simple Umka script
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UmkaLangTestConan(ConanFile):
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
        # Also run the test binary directly to satisfy CI L0d self.run() check
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_umka")
        self.run(test_bin, env="conanrun")
