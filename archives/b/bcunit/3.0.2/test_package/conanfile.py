#!/usr/bin/env python3
"""Conan test_package for bcunit 3.0.2 — real API consumer.

Builds a C consumer against the packaged library (via CMakeDeps) and runs
it; the consumer exits non-zero if the BCUnit counters report anything
other than 2/2 tests run with 0 failures.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BcunitTestConan(ConanFile):
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
        # Run the built consumer directly (product under test is the library;
        # the executable is the vehicle). Binary lands in the build folder,
        # not in the package source directory.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_bcunit"),
            env="conanrun",
        )
