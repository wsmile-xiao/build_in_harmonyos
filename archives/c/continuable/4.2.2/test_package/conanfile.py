#!/usr/bin/env python3
"""Conan consumer test for continuable/4.2.2."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ContinuableTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self.conf.define("tools.build:jobs", 1)
        cmake.build()

    def test(self):
        # test_continuable.cpp contains three independent API assertions.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_continuable"),
            env="conanrun",
        )
