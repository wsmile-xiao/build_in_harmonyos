#!/usr/bin/env python3
"""Conan test_package — gtest 1.17.0."""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class GtestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise Exception("No bindirs found")
            bin_path = os.path.join(bindirs[0], "test_gtest")
            if not os.path.isfile(bin_path):
                raise Exception(f"Test binary not found: {bin_path}")
            self.run(bin_path, env="conanrun")