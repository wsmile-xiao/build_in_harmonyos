#!/usr/bin/env python3
"""Conan test_package for media-control — tests that the binary is executable."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MediacontrolTestConan(ConanFile):
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
        # Run the test binary with conanrun environment
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_media-control")
        self.run(bin_path, env="conanrun")