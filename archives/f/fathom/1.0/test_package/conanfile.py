#!/usr/bin/env python3
"""Test package for fathom 1.0 (installed-package consumer test)."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class FathomTestConan(ConanFile):
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
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindirs[0], "test_fathom")
            self.run(binary, env="conanrun")
        else:
            self.output.info("cross-building: compile+link check only")
