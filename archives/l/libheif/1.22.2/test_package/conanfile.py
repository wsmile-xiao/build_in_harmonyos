#!/usr/bin/env python3
"""Conan test_package for libheif 1.22.2 — L1 smoke test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibheifTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libheif"), env="conanrun")
