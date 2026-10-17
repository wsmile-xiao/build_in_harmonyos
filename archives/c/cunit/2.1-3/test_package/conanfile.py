#!/usr/bin/env python3
"""Conan test_package for cunit — Conan L1 official test.

Verifies that CUnit provides the basic API (CU_initialize, CU_add_suite, CU_run_tests).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CUnitTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_cunit"),
                 env="conanrun")
