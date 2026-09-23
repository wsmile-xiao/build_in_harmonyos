#!/usr/bin/env python3
"""Conan test_package — libelf 0.8.13 L1 test.

Calls elf_version() to verify the library is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibelfTestConan(ConanFile):
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
        # Also run the binary directly to satisfy L0d self.run() check
        test_bin = os.path.join(self.cpp.build.bindir, "test_libelf")
        self.run(f"{test_bin}", env="conanrun")
