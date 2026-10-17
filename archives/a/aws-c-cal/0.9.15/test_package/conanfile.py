#!/usr/bin/env python3
"""Conan test_package — aws-c-cal 0.9.15.

L1 test: compute SHA-256 hash using aws-c-cal API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsccalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require transitive deps so CMakeDeps generates their configs
        self.requires("aws-c-common/0.14.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # Run the test binary directly to ensure it executes on the target platform
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_aws_c_cal"), env="conanrun")
