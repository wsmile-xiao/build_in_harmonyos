#!/usr/bin/env python3
"""Conan test_package for keystone 0.9.2.

Consumer smoke test: verifies the Keystone assembler API by assembling an
ARM64 instruction (mov x0, #0x1) and checking the encoded bytes.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KeystoneTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_keystone"), env="conanrun")
