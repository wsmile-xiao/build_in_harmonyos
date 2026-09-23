#!/usr/bin/env python3
"""Conan test_package for re2c — verifies the re2c binary works.

This test exercises the re2c lexer generator by processing a C file
containing re2c directives and verifying the generated C code compiles
and runs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Re2cTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Use re2c to generate C code from the .re input file
        # env="conanrun" ensures the re2c binary is found in PATH
        output_file = os.path.join(self.build_folder, "generated.c")
        input_file = os.path.join(self.source_folder, "test_input.c")
        self.run(f"re2c -o {output_file} {input_file}", env="conanrun")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.build_folder, "test_re2c"), env="conanrun")
