#!/usr/bin/env python3
"""Conan test_package — enchantum 0.4.0 consumer verification.

Compiles a real C++17 consumer that exercises the enchantum API
(to_string / cast / values_generator) to prove the packaged headers
are usable from a downstream CMake project (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EnchantumTestConan(ConanFile):
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
        # Fall back to running the binary directly (older generators)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_enchantum"), env="conanrun")
