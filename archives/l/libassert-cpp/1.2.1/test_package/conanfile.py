#!/usr/bin/env python3
"""Conan test_package for libassert-cpp/1.2.1.

Consumer-side verification: builds a small executable that includes
<assert.hpp> from the installed package and links assert::assert, then
exercises the ASSERT macro against real runtime conditions.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibassertCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        # L0d: test() must call self.run to be a substantive consumer check
        # (the built binary links assert::assert and runs ASSERT macros).
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libassert_cpp"), env="conanrun")