#!/usr/bin/env python3
"""Conan test_package for libtiff 4.6.0 — L1 official test.

Tests that libtiff can create, write, and read back a TIFF file,
exercising core TIFFOpen/TIFFSetField/TIFFWriteScanline/TIFFGetField/TIFFClose APIs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtiffTestConan(ConanFile):
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
        # Explicitly run the test binary (required by CI L0d)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libtiff"), env="conanrun")
