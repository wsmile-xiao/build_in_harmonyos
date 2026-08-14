#!/usr/bin/env python3
"""Conan test_package for mongoc-driver 1.29.0 — Conan L1 consumer test.

Initializes the mongoc driver, creates a BSON document, and converts it
to JSON to verify the library works end to end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class MongocTestConan(ConanFile):
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
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_mongoc")
            self.run(bin_path, env="conanrun")
