#!/usr/bin/env python3
"""Conan test_package for nghttp3 1.15.0 — L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
The test calls nghttp3_version() and nghttp3_settings_default() to verify
the library is properly linked and functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Nghttp3TestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_nghttp3")
        self.run(test_bin, env="conanrun")
