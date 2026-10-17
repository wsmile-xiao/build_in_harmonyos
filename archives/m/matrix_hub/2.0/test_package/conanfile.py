#!/usr/bin/env python3
"""Conan test_package for matrix_hub 2.0.

Verifies (1) the header-only C API via a real consumer program built against
the installed headers, and (2) the delivered CLI tool Matrix_Hub_v2_0_cli by
running an upstream example script against the packaged binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MatrixhubTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    exports_sources = "test.c", "basic.m"

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
        # Exercise the packaged CLI tool with an upstream example script.
        self.run(
            f"Matrix_Hub_v2_0_cli {os.path.join(self.source_folder, 'basic.m')}",
            env="conanrun",
        )