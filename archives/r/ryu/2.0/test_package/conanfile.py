#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for ryu 2.0.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

test() executes the built consumer binary directly (self.run), which calls
the packaged ryu API (d2s/f2s shortest-representation assertions, buffered_n
length checks, heap APIs, strtod/strtof bit-level round trips) and exits
non-zero on any failed assertion.

File location: archives/r/ryu/2.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RyuTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ryu"), env="conanrun")
