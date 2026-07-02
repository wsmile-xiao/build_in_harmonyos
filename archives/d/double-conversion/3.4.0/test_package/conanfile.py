#!/usr/bin/env python3
"""Conan test_package for double-conversion 3.4.0.

L1 test: Verifies the package can be consumed and the library works correctly.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os
import shutil
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DoubleConversionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Fix compiler paths in generated toolchain before building
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain_file):
            cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
            cxx = shutil.which(os.environ.get("CXX", "clang++")) or "clang++"
            with open(toolchain_file, "r") as f:
                content = f.read()
            content = re.sub(
                r'set\(CMAKE_C_COMPILER "[^"]*"\)',
                f'set(CMAKE_C_COMPILER "{cc}")',
                content
            )
            content = re.sub(
                r'set\(CMAKE_CXX_COMPILER "[^"]*"\)',
                f'set(CMAKE_CXX_COMPILER "{cxx}")',
                content
            )
            with open(toolchain_file, "w") as f:
                f.write(content)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
