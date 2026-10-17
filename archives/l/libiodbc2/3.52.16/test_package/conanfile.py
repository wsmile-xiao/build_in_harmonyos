#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/libiodbc2/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libiodbc2TestConan(ConanFile):
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
        # Run the consumer binary through the generated run environment.
        # The Conan toolchain sets CMAKE_SKIP_RPATH, so the freshly linked
        # binary carries no RUNPATH: `cmake.test()` would launch ctest without
        # LD_LIBRARY_PATH and the process would die at load time
        # ("Error loading shared library libiodbc.so.2 ... symbol not found").
        # Keeping the explicit run (same convention as the sibling a52dec /
        # 7zip test packages) makes the L1 check exercise the packaged .so.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libiodbc2"),
                 cwd=self.cpp.build.bindirs[0], env="conanrun")
