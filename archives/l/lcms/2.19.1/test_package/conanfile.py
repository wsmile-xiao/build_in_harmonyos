#!/usr/bin/env python3
"""Consumer test for lcms (Little CMS) 2.19.1."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LcmsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_lcms")
        self.run(test_binary, env="conanrun")
