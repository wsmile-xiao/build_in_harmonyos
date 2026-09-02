#!/usr/bin/env python3
"""Conan test_package — tl-generator 0.4.0 consumer test (C++).

Compiles and runs a real consumer program that uses tl::generator with
C++20 coroutines, verifying the packaged header works on OHOS aarch64.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class TlGeneratorTestConan(ConanFile):
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
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_tl-generator")
            self.run(bin_path, env="conanrun")
        else:
            self.output.warning("Cannot run consumer binary in this environment")