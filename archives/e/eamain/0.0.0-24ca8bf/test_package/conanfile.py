#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/eamain/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EamainTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # EAMain public headers unconditionally include EABase/EAAssert/EAStdC/
        # EAThread headers, so the consumer test needs those include dirs at
        # compile time. Declaring them as direct requires here ensures CMakeDeps
        # generates full data (include paths) for them in the test_package graph
        # (same approach as the eastdc/0.0.0-fbcc34e test_package).
        self.requires("eabase/0699a15")
        self.requires("eaassert/0.0.0-e5e1812")
        self.requires("eastdc/0.0.0-fbcc34e")
        self.requires("eathread/0.0.0-f3c6c54")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_eamain')}", env="conanrun")
