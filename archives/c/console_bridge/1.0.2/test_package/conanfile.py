#!/usr/bin/env python3
"""Conan test_package for console_bridge 1.0.2.

L1 test: Verifies the package can be consumed and the library works correctly.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class ConsoleBridgeTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: skip binary execution")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No build bindirs found")
        self.run(os.path.join(bindirs[0], "test_console_bridge"), env="conanrun")
