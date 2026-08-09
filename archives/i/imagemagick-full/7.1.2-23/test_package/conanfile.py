#!/usr/bin/env python3
"""Conan test_package for imagemagick-full 7.1.2-23.

L1 test: verifies the package builds and the MagickWand API works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ImagemagickFullTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_imagemagick_full"), env="conanrun")
