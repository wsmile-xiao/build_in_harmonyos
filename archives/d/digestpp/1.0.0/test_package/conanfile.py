#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for digestpp 1.0.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DigestppTestConan(ConanFile):
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
        binary = os.path.join(self.build_folder, "test_digestpp")
        self.run(binary, env="conanrun")