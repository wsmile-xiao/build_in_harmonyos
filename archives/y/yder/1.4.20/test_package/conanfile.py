#!/usr/bin/env python3
"""Consumer test for yder/1.4.20 (logging library)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YderTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindir, "test_yder")
        self.run(f'"{exe}"', env="conanrun")
