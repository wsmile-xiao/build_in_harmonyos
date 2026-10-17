#!/usr/bin/env python3
"""Conan test_package for libchardet 1.0.6."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibchardetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compiled and linked the smoke test only")
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_package build bindirs is empty")
        test_bin = os.path.join(bindirs[0], "test_libchardet")
        self.run(test_bin, env="conanrun")
