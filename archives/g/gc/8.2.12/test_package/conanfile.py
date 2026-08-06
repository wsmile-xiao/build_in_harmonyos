#!/usr/bin/env python3
"""Conan test_package for gc (Boehm GC) 8.2.12.

Conan L1 test: substantively exercises the GC API.
CI runs this automatically via `conan create` (which invokes test_package).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("ctest --output-on-failure", env="conanrun")
