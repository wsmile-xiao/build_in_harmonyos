#!/usr/bin/env python3
"""Conan test_package for libmp3lame 3.100 — L1 official test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libmp3LameTestConan(ConanFile):
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
        # Run test binary directly to verify API linkage (R34/L0d)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libmp3lame"), env="conanrun")
