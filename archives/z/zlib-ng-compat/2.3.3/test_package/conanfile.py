#!/usr/bin/env python3
"""Conan test_package for zlib-ng-compat — Conan L1 official test.

Verifies that zlib-ng-compat provides the standard zlib API
(zlibVersion, deflate, inflate) and links correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZlibNgCompatTestConan(ConanFile):
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
        # L0d: explicit self.run() required by CI gate
        self.run(os.path.join(self.cpp.build.bindir, "test_zlib-ng-compat"),
                 env="conanrun")