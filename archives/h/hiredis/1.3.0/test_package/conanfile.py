#!/usr/bin/env python3
"""Test package for hiredis 1.3.0"""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class HiredisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            bin_path = os.path.join(self.cpp.build.bindir, "test_hiredis")
            self.run(f'"{bin_path}"', env="conanrun")
