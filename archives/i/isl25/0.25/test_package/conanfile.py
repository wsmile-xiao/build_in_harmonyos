#!/usr/bin/env python3
"""Consumer test for isl25 0.25."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            self.output.info("Skipping test_isl execution because this is a cross build")
            return
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindir, "test_isl"), env="conanrun")
