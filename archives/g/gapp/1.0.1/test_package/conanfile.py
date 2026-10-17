#!/usr/bin/env python3
"""Consumer smoke test for gapp — runs the packaged library from a consumer."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GappTestConan(ConanFile):
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
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_gapp")
        self.run(cmd, env="conanrun")
