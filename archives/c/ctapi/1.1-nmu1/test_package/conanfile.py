#!/usr/bin/env python3
"""Conan consumer tests for ctapi 1.1-nmu1."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CtapiTestConan(ConanFile):
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
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_ctapi_c"), env="conanrun")
        self.run(os.path.join(bindir, "test_ctapi_cpp"), env="conanrun")
        self.run(os.path.join(bindir, "test_ctapi_ohos"), env="conanrun")
