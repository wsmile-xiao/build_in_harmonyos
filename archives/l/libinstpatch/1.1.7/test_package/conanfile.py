#!/usr/bin/env python3
"""Conan test_package — consumer verification for libinstpatch 1.1.7.

The published glib package's CMakeDeps metadata carries empty include dirs for
its components, so consumers cannot locate glib.h via CMakeDeps targets.
Upstream libinstpatch itself locates glib via pkg_check_modules, so the test
consumer uses PkgConfigDeps + pkg_check_modules for the glib stack (G2 fix).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibinstpatchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libinstpatch")
        self.run(test_bin, env="conanrun")
