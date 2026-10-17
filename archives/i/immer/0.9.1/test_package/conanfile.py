#!/usr/bin/env python3
"""Test package for immer 0.9.1 — Conan L1 official test.

Compiles test_immer.cpp against the immer header-only library (CMakeDeps
target `immer`) and runs it. Uses Conan's CMakeToolchain for cross-compile.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class ImmerTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_immer"), env="conanrun")
