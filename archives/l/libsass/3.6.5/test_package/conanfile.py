#!/usr/bin/env python3
"""Conan test_package for libsass — API smoke test.

Compiles a SCSS string via libsass C API and verifies the CSS output.
This is NOT a stub — it calls sass_make_data_context/sass_compile_data_context.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibsassTestConan(ConanFile):
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
        # Run the test binary which calls libsass API
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libsass"), env="conanrun")
