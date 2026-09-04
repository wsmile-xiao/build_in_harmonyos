#!/usr/bin/env python3
"""Conan test_package — replxx 0.0.4 (HarmonyOS consumer test).

Builds ohos_spec_test.cxx against the installed replxx package and runs the
resulting test_replxx binary via self.run(). The binary exercises real
replxx API (object lifecycle, history add/size/dedup, state readability);
a non-zero exit from the test binary propagates as a test failure.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ReplxxTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_replxx")
        self.run(test_bin, env="conanrun")
