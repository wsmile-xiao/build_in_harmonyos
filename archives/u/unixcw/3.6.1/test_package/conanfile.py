#!/usr/bin/env python3
"""Conan test_package — unixcw/3.6.1 consumer (L1 official test).

Compiles a small C program that links libcw and exercises the public API
(generator lifecycle, frequency control, Morse sending, version query).
The test() method runs the binary both through CTest and directly via
self.run() (L0d gate requires a self.run() call).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UnixcwTestConan(ConanFile):
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
        binary = os.path.join(self.cpp.build.bindirs[0], "test_unixcw")
        self.run(binary, env="conanrun")
