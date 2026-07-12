#!/usr/bin/env python3
"""Conan test_package — libogg 1.3.5 L1 test.

R34: test calls ogg API (ogg_stream_init/packetin/pageout/clear).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LiboggTestConan(ConanFile):
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
        # R34: run the test binary that calls ogg API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libogg")
        self.run(test_bin, env="conanrun")
