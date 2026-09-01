#!/usr/bin/env python3
"""Conan test_package — clipper2 2.0.1 (polygon clipping library).

L1 test: compile a C++ program that creates polygons and performs
boolean operations (intersection, union), verifying area calculations.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Clipper2TestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_clipper2"), env="conanrun")
