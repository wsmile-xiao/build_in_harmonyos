#!/usr/bin/env python3
"""Conan test_package — glm 0.9.9.8

Consumer-side test: compile a C++ program that uses glm headers
(vec4, mat4, matrix_transform) and verify correctness.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GlmTestConan(ConanFile):
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
        # R34: test must exercise the actual API of the tested package
        # Run the test executable directly to verify glm headers work correctly
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_glm")
        self.run(test_exe, env="conanrun")
