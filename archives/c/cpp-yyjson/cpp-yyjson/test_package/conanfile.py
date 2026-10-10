#!/usr/bin/env python3
"""Consumer tests for the cpp-yyjson Conan package."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CppyyjsonTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_cpp_yyjson"), env="conanrun")
        self.run(os.path.join(bindir, "test_ohos_special"), env="conanrun")
