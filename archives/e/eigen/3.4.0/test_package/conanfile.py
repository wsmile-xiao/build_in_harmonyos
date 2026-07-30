#!/usr/bin/env python3
"""Conan test_package — eigen 3.4.0 consumer test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EigenTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_eigen"), env="conanrun")
