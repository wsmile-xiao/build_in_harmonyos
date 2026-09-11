#!/usr/bin/env python3
"""Conan test_package for libmcfp 1.4.2.

Tests the header-only library by compiling a C++ program that uses
mcfp's command-line parsing API and verifying its behavior.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibmcfpTestConan(ConanFile):
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
        # Run the test binary with actual command-line arguments
        # to exercise mcfp's parsing API (R34: substantive test)
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libmcfp")
        self.run(f"{cmd} --help", env="conanrun")
