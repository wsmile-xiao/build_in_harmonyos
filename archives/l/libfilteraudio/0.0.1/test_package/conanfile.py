#!/usr/bin/env python3
"""Conan test_package for libfilteraudio 0.0.1 — L1 consumer test.

Builds test.c against the *installed* package (CMakeDeps resolves
libfilteraudio::libfilteraudio from package_info) and runs the resulting
binary directly with `self.run(..., env="conanrun")` so the shipped library
is what gets exercised.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfilteraudioTestConan(ConanFile):
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
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libfilteraudio")
        self.run(binary, env="conanrun")
