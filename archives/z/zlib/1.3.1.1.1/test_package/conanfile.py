#!/usr/bin/env python3
"""Conan test_package for zlib 1.3.1.1.1."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZlibTestConan(ConanFile):
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
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_zlib'", env="conanrun")
