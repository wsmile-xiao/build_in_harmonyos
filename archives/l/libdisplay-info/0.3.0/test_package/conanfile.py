#!/usr/bin/env python3
"""Conan test_package — libdisplay-info 0.3.0

L1 test: verify the library API (di_info_parse_edid, di_info_destroy)
is callable and correctly rejects invalid EDID data.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdisplayInfoTestConan(ConanFile):
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
        # Run the test binary directly via self.run() (CI L0d requirement)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdisplay-info")
        self.run(test_bin, env="conanrun")
