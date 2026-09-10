#!/usr/bin/env python3
"""Conan CMake consumer test for libksba 1.6.7."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibksbaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libksba")
        self.run(binary, env="conanrun")
