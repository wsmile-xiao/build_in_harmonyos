#!/usr/bin/env python3
"""Conan test_package — g3log 2.4 consumer test.

Builds a small C++ consumer against the packaged g3log and verifies the
library actually logs (checks the produced log file content).

L0d gate: test() must contain an explicit self.run() for the consumer
binary (E298: avoid delegating to CTest, use VirtualRunEnv + conanrun).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class G3LogTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_g3log")
        self.run(f'"{test_bin}"', env="conanrun")