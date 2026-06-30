#!/usr/bin/env python3
"""Conan test_package for hexcurse — runs the binary to verify it works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HexcurseTestConan(ConanFile):
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
        # Run the hexcurse binary to verify it's functional
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_hexcurse")
        self.run(bin_path, env="conanrun")
