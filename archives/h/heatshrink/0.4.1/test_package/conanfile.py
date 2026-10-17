#!/usr/bin/env python3
"""Conan test_package — heatshrink 0.4.1 real consumer verification.

Builds two real consumers against the packaged libraries:
  - test_heatshrink_dynamic : dynamic-allocation flavor (link heatshrink::dynamic)
  - test_heatshrink_static  : static-allocation flavor  (link heatshrink::static)

Both perform real encode -> decode round trips through the public streaming
API and assert on the results; a nonzero exit fails the test_package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HeatshrinkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        cmake = CMake(self)
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_heatshrink_dynamic"), env="conanrun")
        self.run(os.path.join(bindir, "test_heatshrink_static"), env="conanrun")
