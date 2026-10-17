#!/usr/bin/env python3
"""Conan test_package for duckdb — L1 official test.

CI runs this automatically via conan create (which invokes test_package).
The test binary is aarch64 and executes natively on the OHOS device.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DuckdbTestConan(ConanFile):
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
        # CI gate: test() must execute the consumer binary through a real
        # self.run() step, not only cmake.test().
        binary = os.path.join(self.cpp.build.bindirs[0], "test_duckdb")
        self.run(binary, env="conanrun")
