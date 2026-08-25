#!/usr/bin/env python3
"""Test package for yara — verifies libyara API is usable."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YaraTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly via self.run() (CI L0d requirement)
        exe = os.path.join(self.cpp.build.bindir, "test_package")
        self.run(exe, env="conanrun")
