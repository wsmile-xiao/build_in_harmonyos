#!/usr/bin/env python3
"""Conan test_package — ImageMagick 7.1.2.29

Tests that the MagickWand library is usable by creating
a blank image and querying its dimensions.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ImageMagickTestConan(ConanFile):
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
        # Also run the binary directly to verify --version works
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_imagemagick")
        self.run(f"{bin_path}", env="conanrun")
