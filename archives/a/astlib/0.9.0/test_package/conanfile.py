#!/usr/bin/env python3
"""Conan test_package for astlib — tests that the library API works correctly."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class AstlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require Poco for include directories in test build
        self.requires("poco/1.15.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Pass Poco include dirs to CMake (astlib headers include Poco headers)
        if "poco" in self.dependencies:
            incdirs = self.dependencies["poco"].cpp_info.includedirs
            if incdirs:
                tc.variables["POCO_INCLUDE_DIRS"] = ";".join(incdirs)
        tc.generate()

        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # E298: Use explicit self.run() with conanrun env instead of cmake.test()
        exe = os.path.join(self.cpp.build.bindirs[0], "test_astlib")
        self.run(exe, env="conanrun")
