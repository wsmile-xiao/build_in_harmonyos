#!/usr/bin/env python3
"""Conan test_package for libkaz — consumer-level verification (L1).

Builds a small C program against the installed package and executes it,
exercising the list, dict (including the 1.21 strict-bound lookups) and
hash modules through the public headers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkazTestConan(ConanFile):
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
        # R34: actually execute the consumer binary against the packaged lib.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libkaz"), env="conanrun")
