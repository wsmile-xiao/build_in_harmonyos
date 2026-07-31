#!/usr/bin/env python3
"""Conan L1 test_package for libcgicc."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibcgiccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if cross_building(self):
            return

        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException(
                "test executable directory is unavailable: "
                "cmake_layout() did not define self.cpp.build.bindirs"
            )
        test_bin = os.path.join(bindirs[0], "test_libcgicc")
        self.run(test_bin, env="conanrun")

