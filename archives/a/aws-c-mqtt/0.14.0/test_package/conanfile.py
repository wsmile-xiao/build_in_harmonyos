#!/usr/bin/env python3
"""Conan test_package for aws-c-mqtt 0.14.0.

Verifies the library links and initializes correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwscmqttTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_aws-c-mqtt"), env="conanrun")
