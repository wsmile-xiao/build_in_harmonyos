#!/usr/bin/env python3
"""Conan test_package — astrometry.net 0.98 L1 test."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AstrometrynetTestConan(ConanFile):
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
        # L0d: test() must self.run() the test binary directly (not a stub)
        import os
        binary = os.path.join(self.cpp.build.bindirs[0], "test_astrometry")
        self.run(binary, env="conanrun")