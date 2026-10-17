#!/usr/bin/env python3
"""Conan test_package — real consumer of c-data-structures.

Header-only library: the consumer only sees the installed public headers
tinybuf.h / tinyhashmap.h / tinyhashmap64.h (R34: test() must actually
exercise the library API, not print-only stubs).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CDataStructuresTestConan(ConanFile):
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
        # Run directly as well so stdout/stderr and exit code are observable.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_c-data-structures"),
                 env="conanrun")