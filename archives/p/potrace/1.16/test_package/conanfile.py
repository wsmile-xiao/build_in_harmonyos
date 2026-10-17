#!/usr/bin/env python3
"""Conan test_package for potrace 1.16 — L1 consumer test.

Tests that the potrace library can be linked and its API called.
Uses potrace_version() and potrace_param_default()/potrace_param_free().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PotraceTestConan(ConanFile):
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
        # Run the test binary directly to verify library linkage (R34)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_potrace")
        self.run(test_bin, env="conanrun")
