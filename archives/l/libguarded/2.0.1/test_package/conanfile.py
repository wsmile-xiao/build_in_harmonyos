#!/usr/bin/env python3
"""Conan consumer test for the CsLibGuarded CMake package target."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibguardedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        # Keep the platform identity: the OHOS-adapted Conan toolchain maps
        # os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS.  The consumer project has
        # no platform branches, so no Linux override is needed here.
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer executable was not run")
            return
        consumer = os.path.join(self.cpp.build.bindirs[0], "libguarded_consumer")
        self.run(consumer, env="conanrun")
