#!/usr/bin/env python3
"""Conan test_package — libgpiod 2.0

L1 consumer test: builds a test program that links against libgpiod
and calls actual API functions (gpiod_line_config_new, etc.).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgpiodTestConan(ConanFile):
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
        # Explicit self.run() to run test binary (CI L0d stub check)
        self.run(os.path.join(self.build_folder, "test_libgpiod"), env="conanrun")
