#!/usr/bin/env python3
"""Conan test_package for aws-crt-cpp — L1 official test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwscrtcppTestConan(ConanFile):
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
        # Also run the binary directly for L0d compliance
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_aws_crt_cpp")
        self.run(bin_path, env="conanrun")
