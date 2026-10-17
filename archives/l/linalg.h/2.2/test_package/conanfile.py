#!/usr/bin/env python3
"""Conan test_package — linalg.h 2.2 (header-only consumer test).

Builds test.cpp against the packaged header and runs the binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LinalgHTestConan(ConanFile):
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
        # Run the real consumer binary exercising linalg.h APIs
        self.run(os.path.join(self.cpp.build.bindir, "test_linalg.h"), env="conanrun")
        # Run the HarmonyOS-specific test binary
        self.run(os.path.join(self.cpp.build.bindir, "test_ohos"), env="conanrun")