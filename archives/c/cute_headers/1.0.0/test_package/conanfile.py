#!/usr/bin/env python3
"""Conan test package — cute_headers 1.0.0 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class CuteHeadersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        self.run(os.path.join(self.cpp.build.bindir, "test_cute_headers"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindir, "test_cute_tiled"), env="conanrun")