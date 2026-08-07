#!/usr/bin/env python3
"""Conan test_package for libsamplerate 0.2.2."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsamplerateTestConan(ConanFile):
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
        self.run(os.path.join(self.build_folder, "test_libsamplerate"), env="conanrun")
