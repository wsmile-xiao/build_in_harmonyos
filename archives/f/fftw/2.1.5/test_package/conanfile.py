#!/usr/bin/env python3
"""Conan test_package — fftw 2.1.5 L1 functional test.

Verifies that libsfftw really computes a DFT (delta pulse → all-ones spectrum),
linking the consumer against the packaged static library via CMakeDeps.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FftwTestConan(ConanFile):
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
        # Also run the binary directly to print the functional result
        bindirs = self.cpp.build.bindirs
        if bindirs:
            binpath = os.path.join(bindirs[0], "test_fftw")
            self.run(binpath, env="conanrun")
        else:
            self.run("test_fftw", env="conanrun")
