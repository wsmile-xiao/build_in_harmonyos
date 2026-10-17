#!/usr/bin/env python3
"""Conan test_package for opencore-amr — verifies AMR-NB encode/decode and AMR-WB decode."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpencoreAmrTestConan(ConanFile):
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
        # Also run the binary directly to satisfy R34 (self.run required by CI L0d)
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_opencore_amr")
        self.run(bin_path, env="conanrun")
