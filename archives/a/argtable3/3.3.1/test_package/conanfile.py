#!/usr/bin/env python3
"""Conan consumer test for argtable3 3.3.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Argtable3TestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("Skipping runtime tests while cross-building")
            return

        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_argtable3"
        )
        self.run(executable, env="conanrun")
