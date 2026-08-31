#!/usr/bin/env python3
"""Conan test_package for libaccounts-qt 1.13.

Tests that the library links correctly and the Accounts::Manager API
is accessible. This is a consumer-side smoke test (L1).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout


class LibAccountsQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindir, "test_libaccounts_qt")
        self.run(cmd, env="conanrun")
