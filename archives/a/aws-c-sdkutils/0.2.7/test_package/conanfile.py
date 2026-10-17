#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for aws-c-sdkutils.

Tests that the library initializes correctly and the
aws_partitions_get_supported_version API returns a non-empty result.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsCSdkutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require aws-c-common so CMakeDeps generates its targets
        # (aws-c-common headers are needed by the test source)
        self.requires("aws-c-common/0.14.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to verify the library API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_aws_c_sdkutils")
        self.run(test_bin, env="conanrun")
