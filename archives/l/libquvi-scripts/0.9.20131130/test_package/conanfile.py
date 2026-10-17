#!/usr/bin/env python3
"""Test package for libquvi-scripts 0.9.20131130.

Verifies that the Lua scripts are installed correctly by compiling
a test program that checks for the presence of key script files.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibquviScriptsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
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
        # Pass the package folder to the test binary
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libquvi-scripts")
        pkg_folder = self.dependencies["libquvi-scripts"].package_folder
        self.run(f'{test_bin} "{pkg_folder}"', env="conanrun")
