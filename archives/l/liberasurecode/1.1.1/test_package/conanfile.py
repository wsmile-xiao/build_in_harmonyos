#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/liberasurecode/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LiberasurecodeTestConan(ConanFile):
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
        # ctest would run the binary without the package lib dir on
        # LD_LIBRARY_PATH, so the runtime dlopen() of the backend shared
        # libraries (libXorcode.so.1, libnullcode.so.1, ...) fails.  Run the
        # binary inside the conanrun environment instead.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_liberasurecode"),
                 env="conanrun")
