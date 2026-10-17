#!/usr/bin/env python3
"""Conan test_package - librtas 2.0.4 (R34: real execution, real assertions).

Builds test_package/main.c against the delivered libraries and runs it. The test
binary itself performs 21 assertions across both upstream libraries and exits
non-zero on any failure; see main.c and test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibrtasTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "librtas_test")
        self.run(test_bin, env="conanrun")
