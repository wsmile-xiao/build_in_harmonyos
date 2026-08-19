#!/usr/bin/env python3
"""Conan test_package for argh 1.3.2 — L1 test.

Compiles test.cpp against the argh header-only library and runs it.
Uses Conan's CMakeToolchain for proper cross-compilation support.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ArghTestConan(ConanFile):
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
        test_bin = os.path.join(self.build_folder, "test_argh")
        self.run(test_bin, env="conanrun")
