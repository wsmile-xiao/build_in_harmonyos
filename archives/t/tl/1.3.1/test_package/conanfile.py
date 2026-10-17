#!/usr/bin/env python3
"""Conan test_package — tl 1.3.1 real consumer test (L1).

Builds a standalone C++ consumer against the installed Conan package,
links tl::expected (upstream CMake target) and runs real assertions on
both value and error semantics, returning a non-zero exit code on failure.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TlTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tl"), env="conanrun")
