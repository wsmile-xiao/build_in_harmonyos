#!/usr/bin/env python3
"""Conan test_package for webalizer 2.23.08.

Verifies the webalizer binary runs and reports its version.
R34: test must substantively exercise the packaged binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class WebalizerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.test()
            # Also run the webalizer binary directly to verify it works
            self.run("webalizer -V < /dev/null 2>&1 | grep -q 'Webalizer'", env="conanrun")
