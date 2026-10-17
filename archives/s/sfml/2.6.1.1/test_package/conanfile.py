#!/usr/bin/env python3
"""Conan test_package for SFML 2.6.1.1.

Verifies that downstream code can include and link the packaged System and
Network modules, then runs a small API smoke test.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SfmlTestConan(ConanFile):
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
        if not can_run(self):
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_sfml executable directory was not produced")
        self.run(os.path.join(bindirs[0], "test_sfml"), env="conanrun")
