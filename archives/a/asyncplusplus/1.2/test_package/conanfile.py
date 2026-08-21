#!/usr/bin/env python3
"""Conan test_package for asyncplusplus 1.2 — L1 consumer test.

Verifies that the built async++ library can be linked and used by a downstream
C++ program. Exercises: task creation, task scheduling, continuation, parallel_for.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class AsyncplusplusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir[0], "test_asyncplusplus")
            self.run(bin_path, env="conanrun")
