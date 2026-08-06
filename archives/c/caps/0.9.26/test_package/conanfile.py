#!/usr/bin/env python3
"""Conan test_package for caps — verifies LADSPA plugin loads correctly."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CapsTestConan(ConanFile):
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
        # R34: Execute test binary — verifies LADSPA plugin descriptor is callable
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_caps")
        self.run(test_bin, env="conanrun")
