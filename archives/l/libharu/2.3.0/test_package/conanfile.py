#!/usr/bin/env python3
"""Conan test_package for libharu 2.3.0 — Conan L1 official test.

E298 fix: the consumer links the shared libhpdf.so; running it through
`cmake.test()` does not activate the Conan run environment, so the dynamic
loader cannot find libhpdf.so at runtime (Error loading shared library).
VirtualRunEnv generates the conanrun env and `self.run(..., env='conanrun')`
executes the consumer with LD_LIBRARY_PATH/PATH from that env.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibharuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # E298: run the real consumer binary with the conanrun environment so
        # libhpdf.so (and libpng/libz) resolve at runtime; not a print stub.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libharu")
        self.run(f'"{test_bin}"', env="conanrun")