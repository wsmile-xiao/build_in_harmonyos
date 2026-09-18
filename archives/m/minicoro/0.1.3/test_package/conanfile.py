#!/usr/bin/env python3
"""Conan consumer test for minicoro 0.1.3."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MinicoroTestConan(ConanFile):
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
        build_dir = self.cpp.build.bindirs[0]
        for binary in ("test_minicoro", "test_ohos_platform"):
            test_binary = os.path.join(build_dir, binary)
            self.run(test_binary, env="conanrun")