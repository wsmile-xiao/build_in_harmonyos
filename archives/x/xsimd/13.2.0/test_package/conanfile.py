#!/usr/bin/env python3
"""Conan test_package — xsimd 13.2.0 consumer test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XsimdTestConan(ConanFile):
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
        exe = "test_xsimd.exe" if self.settings.os == "Windows" else "test_xsimd"
        self.run(os.path.join(self.cpp.build.bindirs[0], exe), env="conanrun")
