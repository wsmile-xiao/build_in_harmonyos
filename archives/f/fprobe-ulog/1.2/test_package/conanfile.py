#!/usr/bin/env python3
"""Test package for fprobe-ulog 1.2.

Verifies that the fprobe-ulog binary is installed and functional.
R34: Test must actually execute the tested package's binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class FprobeUlogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
            # R34: Run the test binary that exercises the fprobe-ulog binary
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_fprobe_ulog")
            self.run(f'"{bin_path}"', env="conanrun")
