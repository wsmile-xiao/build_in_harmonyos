#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for aws-checksums 0.2.10.

Verifies CRC32 and CRC32C computation against standard check values.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class AwsChecksumsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require aws-c-common for the test_package
        self.requires("aws-c-common/0.14.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to verify CRC32/CRC32C correctness
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_aws_checksums")
        self.run(test_bin, env="conanrun")
