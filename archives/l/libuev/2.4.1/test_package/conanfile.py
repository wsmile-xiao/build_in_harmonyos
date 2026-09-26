#!/usr/bin/env python3
"""Conan test_package — libuev 2.4.1 L1 consumer test.

Builds test.c against the installed libuev package via public header
uev/uev.h and public API, then runs it (Conan L1 test).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibuevTestConan(ConanFile):
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
        # Run the consumer binary directly (L0d requires an explicit run)
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libuev"), env="conanrun")
