#!/usr/bin/env python3
"""Conan test_package for alembic 1.8.10 — Conan L1 consumer test.

Builds a small program that links libAlembic (+ vendored libImath), writes an
Ogawa archive and reads it back, verifying the Alembic API end to end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class AlembicTestConan(ConanFile):
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
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_alembic")
            self.run(bin_path, env="conanrun")
