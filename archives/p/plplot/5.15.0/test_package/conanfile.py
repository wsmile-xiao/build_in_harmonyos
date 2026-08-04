#!/usr/bin/env python3
"""Consumer test for plplot 5.15.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PlplotTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_plplot")
        self.run(test_bin, env="conanrun")
