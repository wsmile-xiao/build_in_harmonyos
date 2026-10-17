#!/usr/bin/env python3
"""Conan test_package — blake2 20190724.

Compiles a small program that calls the blake2b() and blake2s() one-shot
APIs from the installed libblake2 and verifies the resulting digests
against the official BLAKE2 test vectors (empty-input digests hardcoded
in test.c, sourced from the official blake2-kat.h vectors).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Blake2TestConan(ConanFile):
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
        # Run the compiled test binary directly (L0d: must use self.run)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_blake2"), env="conanrun")
