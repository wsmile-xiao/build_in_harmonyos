#!/usr/bin/env python3
"""Conan test_package — libdivide 5.3.0

Consumer-side test: compile a C++ program that uses the libdivide C++ API
to construct scalar dividers and perform optimized integer division,
verifying the results match plain division.

Only the most basic, portable scalar API is exercised — no SSE/AVX/AVX512
or other x86-specific paths are forced.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdivideTestConan(ConanFile):
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
        # R34: test must exercise the actual API of the tested package
        # Run the test executable directly to verify libdivide headers work
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_libdivide")
        self.run(test_exe, env="conanrun")
