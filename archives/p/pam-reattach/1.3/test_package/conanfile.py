#!/usr/bin/env python3
"""Conan test_package — pam-reattach 1.3."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PamReattachTestConan(ConanFile):
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
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_pam_reattach")
        self.run(bin_path, env="conanrun")
