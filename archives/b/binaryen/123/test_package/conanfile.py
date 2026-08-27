#!/usr/bin/env python3
"""Test package — binaryen 123.

Smoke test: build a minimal binary, then run wasm-opt --version
from the package to verify the tools work (R34: execute package binary).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BinaryenTestConan(ConanFile):
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
        # Also verify wasm-opt from the package works
        self.run("wasm-opt --version", env="conanrun")
