#!/usr/bin/env python3
"""Conan test_package — libnfnetlink 1.0.2 L1 test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibnfnetlinkTestConan(ConanFile):
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
        # L1: Execute test binary to verify library linkage
        self.run(os.path.join(self.build_folder, "test_libnfnetlink"), env="conanrun")
