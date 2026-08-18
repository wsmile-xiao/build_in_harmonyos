#!/usr/bin/env python3
"""Conan test_package for exiv2 — Conan L1 official test.

Verifies the exiv2 library is correctly built and linked by exercising its
core EXIF metadata write/read API (ExifData, Exiv2::version). See R34.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Exiv2TestConan(ConanFile):
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
        # Run the test binary directly so failures surface as non-zero exit
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_exiv2")
        self.run(cmd, env="conanrun")
