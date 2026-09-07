#!/usr/bin/env python3
"""Conan test_package — open-tyrian 2.1.20221123

Consumer-side test: builds a test executable that runs the opentyrian
binary with --help to verify it's functional.

Upstream has no test suite (game project).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpentyrianTestConan(ConanFile):
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
        # R34: test must exercise the actual package binary
        # Run the test executable which calls system("opentyrian --help")
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_open-tyrian")
        self.run(test_exe, env="conanrun")
