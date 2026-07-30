#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/argon2/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Argon2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # -j1: OHOS does not support mkfifo (make jobserver)
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        cmake = CMake(self)
        cmake.test(build_tool_args=["-j1"])
        # Direct binary verification (also satisfies L0d self.run check)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_argon2"), env="conanrun")
