#!/usr/bin/env python3
"""Conan test_package — atf 0.23

L1 test: verify the package can be consumed and linked.
Uses atf-c API to write real test cases.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AtfTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_atf")
        # ATF test programs require a test case name argument
        # Run all three test cases to verify atf-c API functionality
        for tc in ("pass_test", "str_compare_test", "math_test"):
            self.run(f"{test_bin} {tc}", env="conanrun")
