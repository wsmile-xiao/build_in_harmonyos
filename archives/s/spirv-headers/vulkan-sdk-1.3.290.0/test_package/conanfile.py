#!/usr/bin/env python3
"""Conan consumer test for SPIRV-Headers."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SpirvHeadersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(
            self.cpp.build.bindir, "spirv_headers_test"
        )
        if can_run(self):
            self.run(executable, env="conanrun")
        else:
            self.output.info(
                "Cross-building: SPIR-V consumer compiled; runtime not executed"
            )
