#!/usr/bin/env python3
"""Conan test_package — libxosd 2.2.14 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxosdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        # libxosd::libxosd transitively requires libx11 / libxext / libxinerama
        # via cpp_info.requires, so the test only needs the library itself.
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_libxosd")
        self.run(test_bin, env="conanrun")
