#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for rapidyaml 0.7.2.

Builds a small C++ program that parses and emits YAML through the installed
rapidyaml headers/library and asserts round-trip correctness. Serves as the
real HarmonyOS-specific test case: it must compile against the packaged
headers and link against libryml on the OHOS/PC target.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RapidYamlTestConan(ConanFile):
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
        # L0d: run the built consumer test binary directly via self.run()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_rapidyaml")
        self.run(bin_path, env="conanrun")
