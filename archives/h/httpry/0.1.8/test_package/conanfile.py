#!/usr/bin/env python3
"""Conan test_package for httpry 0.1.8.

Verifies that the httpry binary is installed and functional by running
it with -h flag and checking the output contains version info.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class HttpryTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_httpry")
            httpry = os.path.join(self.dependencies["httpry"].package_folder, "bin", "httpry")
            self.run(f'HTTPRY_PATH="{httpry}" "{test_bin}"', env="conanrun")
