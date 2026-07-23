#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/metis/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MetisTestConan(ConanFile):
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
        # R34: Run the test binary that calls METIS_PartGraphRecursive API
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_metis')}", env="conanrun")
