#!/usr/bin/env python3
"""Conan test_package for libspng 0.7.4.

No external PNG binaries in PR (CI checkout-pr cannot apply binary diffs).
Real API usage: encode RGBA8 -> PNG -> decode -> pixel compare + version check
= 7 CTest cases / 28 assertions, PNGs built in-memory via zlib.
"""
from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.layout import basic_layout


class LibspngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("ctest --output-on-failure", env="conanrun")
