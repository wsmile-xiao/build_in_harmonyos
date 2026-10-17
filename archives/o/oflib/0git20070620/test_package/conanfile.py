#!/usr/bin/env python3
"""Consumer tests for the oflib package."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OflibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        api_test = os.path.join(bindir, "oflib_tests")
        platform_test = os.path.join(bindir, "oflib_ohos_platform_test")
        for scenario in ("uint32", "uint64", "device-tree"):
            self.run(f'"{api_test}" {scenario}', env="conanrun")
        self.run(f'"{platform_test}"', env="conanrun")
