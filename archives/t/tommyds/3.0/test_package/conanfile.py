#!/usr/bin/env python3
"""Conan test_package — tommyds 3.0 consumer test.

Builds test.c (which exercises the tommy_hashtable API from the installed
package) and runs the resulting binary — R34: genuinely links and calls the
library, not a print-only stub.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TommydsTestConan(ConanFile):
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
        # Run the consumer binary directly (ctest path also available via
        # CMakeLists enable_testing/add_test).
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tommyds"),
                 env="conanrun")
