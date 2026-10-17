#!/usr/bin/env python3
"""Conan test_package — libiconv 1.17.1.

R34: Test actually calls libiconv API (iconv_open/iconv/iconv_close).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibiconvTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libiconv"), env="conanrun")
