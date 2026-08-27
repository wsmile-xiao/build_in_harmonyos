#!/usr/bin/env python3
"""Conan test_package for aws-c-sdkutils 0.2.4 — Conan L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
File location: archives/a/aws-c-sdkutils/0.2.4/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwscsdkutilsTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_aws_c_sdkutils"), env="conanrun")
