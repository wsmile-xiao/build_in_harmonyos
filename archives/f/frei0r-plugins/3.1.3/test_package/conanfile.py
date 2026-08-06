#!/usr/bin/env python3
"""Conan test_package for frei0r-plugins 3.1.3 — Conan L1 official test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Frei0rPluginsTestConan(ConanFile):
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
        # Run the test binary directly to verify it works (L0d: self.run required)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_frei0r"), env="conanrun")
