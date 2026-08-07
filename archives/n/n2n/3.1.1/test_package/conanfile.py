#!/usr/bin/env python3
"""Conan test_package for n2n — consumer perspective validation.

Tests n2n's pearson hash and wire protocol encode/decode functions.
These are self-contained API functions that don't require TUN/TAP or network.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class N2NTestConan(ConanFile):
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
        # Run the test binary directly (L0d requires self.run())
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_n2n")
        self.run(test_binary, env="conanrun")
