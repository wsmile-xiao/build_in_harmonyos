#!/usr/bin/env python3
"""Conan test_package for libjodycode — L1 test that exercises the library API."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibjodycodeTestConan(ConanFile):
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
        # Run the test binary directly to exercise libjodycode API (R34, L0d)
        exe = os.path.join(self.cpp.build.bindir, "test_libjodycode")
        self.run(exe, env="conanrun")
