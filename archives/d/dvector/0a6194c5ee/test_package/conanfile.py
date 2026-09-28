#!/usr/bin/env python3
"""Consumer test for dvector 0a6194c5ee (header-only C math library)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DvectorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_C_STANDARD"] = "99"
        tc.cache_variables["CMAKE_C_STANDARD_REQUIRED"] = True
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_dvector")
        self.run(executable, env="conanrun")
