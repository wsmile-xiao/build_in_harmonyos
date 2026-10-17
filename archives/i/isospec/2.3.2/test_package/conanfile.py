#!/usr/bin/env python3
"""Conan test_package driver — isospec 2.3.2.

Runs the consumer test and the HarmonyOS-specific test directly
(`self.run(..., env="conanrun")`); cmake.test() is deliberately avoided.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IsoSpecTestConan(ConanFile):
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
        bindir = self.cpp.build.bindir
        # Run the binaries directly (conanrun env provides the library path).
        self.run(os.path.join(bindir, "test_isospec"), env="conanrun")
        if self.settings.os == "OHOS":
            self.run(os.path.join(bindir, "test_isospec_ohos"), env="conanrun")
