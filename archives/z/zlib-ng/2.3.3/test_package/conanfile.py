#!/usr/bin/env python3
"""Conan test_package for zlib-ng - Conan L1 official test.

Verifies that zlib-ng provides the native zlib-ng API
(zng_compressBound, zng_compress, zng_uncompress) via <zlib-ng.h>
and links correctly against libz-ng.a.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZlibNgTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindir, "test_zlib-ng"),
                 env="conanrun")
