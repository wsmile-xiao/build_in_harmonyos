#!/usr/bin/env python3
"""Conan test_package for zziplib 0.13.78 — Conan L1 official test.

Uses CMake to build the test.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZziplibTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindir, "test_zziplib"), env="conanrun")