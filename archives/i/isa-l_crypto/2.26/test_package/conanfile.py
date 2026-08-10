#!/usr/bin/env python3
"""Conan test_package for isa-l_crypto 2.26.

Tests the MD5 multi-buffer API by computing MD5("abc")
and comparing against the known digest.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IsaLCryptoTestConan(ConanFile):
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
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_isal_crypto')}", env="conanrun")
