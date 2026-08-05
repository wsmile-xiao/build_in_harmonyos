#!/usr/bin/env python3
"""Test package for expected-lite 0.6.3 (header-only C++ expected library)"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class ExpectedLiteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_expected_lite"), env="conanrun")
