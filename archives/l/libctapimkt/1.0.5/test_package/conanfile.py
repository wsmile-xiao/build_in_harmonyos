#!/usr/bin/env python3
"""Conan test_package — libctapimkt 1.0.5 (R34: 实质调用被测包 API)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibctapimktTestConan(ConanFile):
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
        # Also run the shipped CLI tool (R38: mktlin is installed to bin/)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libctapimkt"), env="conanrun")
