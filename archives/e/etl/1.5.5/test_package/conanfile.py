#!/usr/bin/env python3
"""Conan test_package for ETL (Extended Template Library) 1.5.5.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

The test verifies that:
1. The ETL header files are correctly installed
2. The ETL handle (smart pointer) template can be instantiated
3. Reference counting and handle operations work correctly
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EtlTestConan(ConanFile):
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
        # L0d: explicit self.run() to run the compiled test binary,
        # proving the test_package substantially exercises ETL (R34).
        self.run(os.path.join(self.cpp.build.bindir, "test_etl"), env="conanrun")
