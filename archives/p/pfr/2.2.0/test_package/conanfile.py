#!/usr/bin/env python3
"""Conan test package for Boost.PFR 2.2.0 consumer checks."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PfrTestConan(ConanFile):
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
        for executable in ("test_pfr", "test_pfr_cxx20"):
            self.run(os.path.join(self.cpp.build.bindirs[0], executable), env="conanrun")
