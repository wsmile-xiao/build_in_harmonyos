#!/usr/bin/env python3
"""Conan test_package for lzo 2.10 — L1 test (R34 compliant)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LzoTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lzo")
        self.run(test_bin, env="conanrun")
