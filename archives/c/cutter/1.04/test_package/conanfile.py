#!/usr/bin/env python3
"""Test package for cutter 1.04.

Builds and runs a test that executes the cutter binary (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CutterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: Run test_cutter which executes the actual cutter binary
        exe = os.path.join(self.build_folder, "test_cutter")
        self.run(f'"{exe}"', env="conanrun")
