#!/usr/bin/env python3
"""Conan test_package for p8-platform 2.1.0 — L1 consumer-side test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class P8PlatformTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_p8_platform")
        self.run(test_bin, env="conanrun")
