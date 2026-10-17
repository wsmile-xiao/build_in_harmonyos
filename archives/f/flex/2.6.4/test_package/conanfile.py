#!/usr/bin/env python3
"""Conan test_package for flex — Fast Lexical Analyzer Generator.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/f/flex/2.6.4/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FlexTestConan(ConanFile):
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
        if not self.cpp.build.bindirs:
            raise FileNotFoundError("build bindirs is empty — no test binary directory")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_flex")
        self.run(bin_path, env="conanrun")
