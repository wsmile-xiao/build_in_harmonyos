#!/usr/bin/env python3
"""Conan test_package for mongoose 7.21."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MongooseTestConan(ConanFile):
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
        # Run the test binary directly (R34: must actually test the package API)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_mongoose")
        self.run(exe, env="conanrun")
