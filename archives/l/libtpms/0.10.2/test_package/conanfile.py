#!/usr/bin/env python3
"""Conan consumer test for libtpms 0.10.2."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibtpmsTestConan(ConanFile):
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
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libtpms")
        self.run(executable, env="conanrun")
