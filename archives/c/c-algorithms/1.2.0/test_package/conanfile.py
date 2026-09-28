#!/usr/bin/env python3
"""Conan test_package — c-algorithms 1.2.0 consumer (Conan L1 official test).

CI runs this automatically via `conan create` (which invokes test_package).
L0d: test() must call self.run to really execute the tested binary (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CalgorithmsTestConan(ConanFile):
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
        # Run the consumer binary directly (R34: real API exercise, not a stub)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_c-algorithms"),
                 env="conanrun")
        cmake = CMake(self)
        cmake.test()