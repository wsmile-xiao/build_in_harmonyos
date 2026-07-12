#!/usr/bin/env python3
"""Conan test_package — flac/1.4.3 consumer test.

Verifies that libFLAC links correctly and OGG support is enabled.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FlacTestConan(ConanFile):
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
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_flac")
        self.run(cmd, env="conanrun")
