#!/usr/bin/env python3
"""Conan test_package for Nuklear 4.12.8."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class NuklearTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "cross-building: compile/link consumer test completed; "
                "execution is left to native OHOS CI"
            )
            return

        exe = os.path.join(self.cpp.build.bindirs[0], "test_nuklear")
        self.run(exe, env="conanrun")
