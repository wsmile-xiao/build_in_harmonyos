#!/usr/bin/env python3
"""Conan test_package — nettle 3.9.1 consumer test.

Links against nettle and verifies real crypto primitives: SHA256('abc')
digest and AES-128 block encryption, both asserted against known-good
results. Any mismatch returns non-zero.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class NettleTestConan(ConanFile):
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
        # Run the consumer binary directly; CTest above verifies the same
        # executable and its return status.
        harness = os.path.join(self.cpp.build.bindirs[0], "test_nettle")
        self.run(harness, env="conanrun")