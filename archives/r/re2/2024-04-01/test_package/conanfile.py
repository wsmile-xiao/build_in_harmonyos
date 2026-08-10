#!/usr/bin/env python3
"""Conan test_package for re2 2024-04-01.

Tests that re2 builds, links, and matches regex patterns correctly.
Uses the same absl_DIR workaround as the parent conanfile.py.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Re2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Point find_package(absl) to the real abseil-cpp cmake config
        # so re2's targets resolve the absl::* dependencies.
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_re2")
        self.run(cmd, env="conanrun")
