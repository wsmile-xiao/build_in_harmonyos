#!/usr/bin/env python3
"""Conan test_package — libutf8proc 2.10.0 L1 test.

R34: test calls utf8proc API (utf8proc_version / utf8proc_map NFKC).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libutf8procTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libutf8proc")
        self.run(test_bin, env="conanrun")
