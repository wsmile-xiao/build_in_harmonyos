#!/usr/bin/env python3
"""Conan test_package for fftw 3.3.10.1."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FftwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_exe = os.path.join(self.build_folder, "test_fftw")
        self.run(test_exe, env="conanrun")
