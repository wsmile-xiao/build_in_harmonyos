#!/usr/bin/env python3
"""Conan test_package for cityhash 1.1.1.

Compiles a consumer program against the packaged headers and library and
asserts CityHash64/32 outputs against fixed reference values (captured from
the upstream cityhash_unittest reference vectors on this same release).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CityhashTestConan(ConanFile):
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
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_cityhash")
            self.run(cmd, env="conanrun")
