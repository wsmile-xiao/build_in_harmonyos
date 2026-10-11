#!/usr/bin/env python3
"""Conan test_package for libgphoto2 2.5.31.

Tests that the libgphoto2 library can be linked and its API called.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libgphoto2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libtool/2.5.4.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly instead of cmake.test() (avoids HMDFS mkfifo issues)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
