#!/usr/bin/env python3
"""Conan test_package for simdjson 3.9.5 — validates the simdjson API works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SimdjsonTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_simdjson")
        self.run(test_bin, env="conanrun")
        test_bin_harmonyos = os.path.join(self.cpp.build.bindirs[0], "test_harmonyos")
        self.run(test_bin_harmonyos, env="conanrun")