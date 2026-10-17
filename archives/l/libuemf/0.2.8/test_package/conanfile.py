#!/usr/bin/env python3
"""Conan test_package for libuemf — L1 consumer test.

Builds test_libuemf_api.c against the installed package and runs it; the
binary asserts a create/read/walk round trip through the public API and
returns non-zero on any failed check (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibuemfTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libuemf"),
                 env="conanrun")
