#!/usr/bin/env python3
"""Conan test_package - libosmium 2.23.0.

Consumer test: compiles against the installed headers and calls the real
OSM data model API (OSMNode id/version/timestamp/location/user) plus the
version macro contract.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibosmiumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Run the consumer binary directly (visible self.run for the L0d
        # static gate; ctest alone hides the actual execution).
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libosmium")
        self.run(exe, env="conanrun")
