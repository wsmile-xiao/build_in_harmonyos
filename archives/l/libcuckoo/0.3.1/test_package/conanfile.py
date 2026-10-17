#!/usr/bin/env python3
"""Conan test_package — libcuckoo 0.3.1 L1 test.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibcuckooTestConan(ConanFile):
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
        # Directly run the test binary as well (CI L0 gate requirement)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libcuckoo"), env="conanrun")
