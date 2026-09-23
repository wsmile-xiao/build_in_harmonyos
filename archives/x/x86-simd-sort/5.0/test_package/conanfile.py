#!/usr/bin/env python3
"""Conan test_package for x86-simd-sort 5.0.

L1 official consumer test: builds a real consumer executable that uses only
the installed public header <x86simdsort.h> and exported API
(x86simdsort::qsort / argsort), then runs it and checks its observable result.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class X86SimdsortTestConan(ConanFile):
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
        # The library is a shared .so; the conanrun environment (from the
        # recipe's runenv_info LD_LIBRARY_PATH) makes the loader find the
        # package's lib dir before executing the consumer binary.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_x86-simd-sort")
        self.run(str(bin_path), env="conanrun")