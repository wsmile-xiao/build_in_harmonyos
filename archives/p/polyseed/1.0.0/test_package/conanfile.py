#!/usr/bin/env python3
"""Conan test_package for polyseed/1.0.0 (L1 consumer test).

Per knowledge E298: run the consumer binary explicitly with the conanrun
environment instead of delegating execution to CTest.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PolyseedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        shared = str(self.dependencies["polyseed"].options.shared)
        tc.variables["POLYSEED_PKG_SHARED"] = shared
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        matches = glob.glob(
            os.path.join(self.build_folder, "**", "test_polyseed"), recursive=True
        )
        assert matches, "test_polyseed consumer binary not found"
        self.run(f'"{matches[0]}"', env="conanrun")
