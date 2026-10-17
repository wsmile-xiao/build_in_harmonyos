#!/usr/bin/env python3
"""Conan test_package — libblockdev 3.4.0.

Tests that the libblockdev library and loop plugin are correctly
linked and their API functions are callable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibblockdevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libblockdev headers include glib.h, so we need glib2 for the test
        self.requires("glib2/2.88.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Also run the test binary directly (R34: test must exercise the package)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libblockdev"), env="conanrun")
