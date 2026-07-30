#!/usr/bin/env python3
"""Conan test_package — draco 1.5.7

L1 test: compile and link against libdraco, then run encode/decode smoke test.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class DracoTestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_draco")
            self.run(f"{bin_path}", env="conanrun")
        else:
            self.output.info("Cross-building: compile-only test passed")