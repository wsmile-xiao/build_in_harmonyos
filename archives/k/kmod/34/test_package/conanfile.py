#!/usr/bin/env python3
"""Conan test_package — kmod 34 L1 test.

R34: test calls libkmod API (kmod_new / kmod_get_dirname /
kmod_module_new_from_name / kmod_module_get_name).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KmodTestConan(ConanFile):
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
        # R34: run the test binary that calls libkmod API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_kmod")
        self.run(test_bin, env="conanrun")
