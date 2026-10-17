#!/usr/bin/env python3
"""Conan test_package — libredblack 1.3 consumer test.

Builds a C99 consumer against the installed libredblack and runs it.  The
consumer inserts 200 keys in descending order and checks find/min/max/ordering/
range lookups/walk/delete through the public <redblack.h> API (see
src/test_libredblack.c).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibredblackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libredblack")
        self.run(test_bin, env="conanrun")
