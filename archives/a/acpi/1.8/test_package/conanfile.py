#!/usr/bin/env python3
"""Conan test_package — acpi 1.8 binary smoke test.

Tests that the package can be consumed and a test program builds.
The L2 smoke test in conan-verify handles running the actual binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AcpiTestConan(ConanFile):
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
