#!/usr/bin/env python3
"""Conan test_package — libaccounts-glib 1.27.

This test verifies the GObject type system is properly initialized when
linking against libaccounts-glib, ensuring the library and its glib2
dependency chain are correctly linked.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibAccountsGlibTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Run the test binary directly to verify the library is functional
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libaccounts-glib"),
                 env="conanrun")
