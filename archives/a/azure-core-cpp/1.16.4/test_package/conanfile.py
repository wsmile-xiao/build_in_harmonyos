#!/usr/bin/env python3
"""Conan test_package for azure-core-cpp 1.16.4 — Conan L1 official test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AzureCoreCppTestConan(ConanFile):
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
        # L0d gate (CI) requires at least one self.run() call inside test()
        # to verify real test execution at consumer level.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_azure-core-cpp"),
                 env="conanrun")