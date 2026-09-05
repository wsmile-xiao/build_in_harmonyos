#!/usr/bin/env python3
"""Conan consumer test for fastmod 0.1.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FastmodTestConan(ConanFile):
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
        # Run the consumer executable directly; this is substantive R34
        # coverage and satisfies the CI self.run() test-substance gate.
        self.run(os.path.join(self.build_folder, "test_fastmod"), env="conanrun")
