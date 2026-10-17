#!/usr/bin/env python3
"""test_package for masscan — verifies the masscan binary works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MasscanTestConan(ConanFile):
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
        # Run the masscan binary and verify its version output (R34)
        # masscan --version exits with code 1 by design;
        # we pipe through grep to verify the output contains the expected string
        self.run("masscan --version 2>&1 | grep -q 'Masscan version'", env="conanrun")
