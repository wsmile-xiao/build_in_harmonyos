#!/usr/bin/env python3
"""Conan test_package — aws-lc 5.5.0 L1 test.

L1 test in the five-level test system. CI runs this automatically via
`conan create` (which invokes test_package).

File location: archives/a/aws-lc/5.5.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwslcTestConan(ConanFile):
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
        test_exe = os.path.join(self.cpp.build.bindir, "test_aws-lc")
        self.run(test_exe, env="conanrun")
