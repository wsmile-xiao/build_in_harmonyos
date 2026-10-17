#!/usr/bin/env python3
"""Conan test_package for md4c 0.5.3.

Builds and runs a consumer test that links the packaged md4c library and
exercises the real md_parse() SAX-like parser API (not just an include
check). The test verifies that block/span/text callbacks fire correctly
for a heading and bold inline text.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Md4cTestConan(ConanFile):  # noqa: N801
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
        # Run the test binary directly as an additional explicit check.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_md4c"), env="conanrun")
