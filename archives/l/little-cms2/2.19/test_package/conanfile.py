#!/usr/bin/env python3
"""Conan test_package — little-cms2 2.19 consumer test.

Builds a C99 consumer against the installed liblcms2 and runs it.  The consumer
does a real colour-management round trip — sRGB profile -> Lab profile ->
transform -> known colours — so a package that links but does not work cannot
pass (see src/test_lcms2.c).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LittleCms2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lcms2")
        self.run(test_bin, env="conanrun")
