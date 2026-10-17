#!/usr/bin/env python3
"""Conan test_package for libstemmer 3.1.1 — Conan L1 official test.

Verifies that the libstemmer package can be consumed and the stemming
API works correctly. Uses CMake (CMakeDeps + CMakeToolchain) so the
compiler is handled by Conan toolchain (R33).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibStemmerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R5: OHOS has no /bin/sh, use bash to run the binary
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_libstemmer'", env="conanrun")
