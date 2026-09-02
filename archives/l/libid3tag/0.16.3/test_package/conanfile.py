#!/usr/bin/env python3
"""Conan test_package for libid3tag 0.16.3 — L1 official test.

Verifies that the libid3tag library is properly linked and its API is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libid3tagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # id3tag.h does not include zlib headers, but linking the test
        # executable resolves id3tag's zlib symbols through the consumer.
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: Run the test binary that calls libid3tag API
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libid3tag')}", env="conanrun")
