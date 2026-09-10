#!/usr/bin/env python3
"""Installed-package consumer test for cimfomfa."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CimfomfaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        binary = os.path.join(self.cpp.build.bindir, "test_cimfomfa")
        self.run(binary, env="conanrun")
        harmonyos_binary = os.path.join(
            self.cpp.build.bindir, "test_cimfomfa_harmonyos"
        )
        self.run(harmonyos_binary, env="conanrun")
