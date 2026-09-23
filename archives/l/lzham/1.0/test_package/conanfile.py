#!/usr/bin/env python3
"""Conan consumer test for LZHAM 1.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LzhamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.variables["LZHAM_OHOS_TEST"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bins = ["test_lzham"]
        if str(self.settings.os) == "OHOS":
            test_bins.append("test_lzham_ohos")
        for test_name in test_bins:
            test_bin = os.path.join(self.cpp.build.bindirs[0], test_name)
            self.run(test_bin, env="conanrun")
