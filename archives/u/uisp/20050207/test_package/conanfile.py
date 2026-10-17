#!/usr/bin/env python3
"""Conan test_package — uisp L1 test.

Builds a tiny launcher that executes the packaged `uisp` binary with
--version and asserts exit code 0 (R34: real execution, no stub).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UispTestConan(ConanFile):
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
        uisp_bin = os.path.join(self.dependencies["uisp"].cpp_info.bindirs[0], "uisp")
        self.run(f"\"{uisp_bin}\" --version")
