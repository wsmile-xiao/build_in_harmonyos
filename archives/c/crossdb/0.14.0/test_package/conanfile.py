#!/usr/bin/env python3
"""Conan test_package for crossdb 0.14.0 — Conan L1 official test.

This is the L1 test in the five-level test system; CI runs it automatically
via `conan create`, which builds this consumer against the packaged recipe
and then executes it.

File location: archives/c/crossdb/0.14.0/test_package/conanfile.py
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CrossdbTestConan(ConanFile):
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
        # PF3/L0c: run the real consumer binary (assertion failures make the
        # process exit non-zero, so a broken package cannot pass silently).
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found in test_package layout")
        bin_path = os.path.join(bindirs[0], "test_crossdb")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")
        self.run(bin_path, env="conanrun")
