#!/usr/bin/env python3
"""Conan consumer test for the PhysUnits-CT CMake package target."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PhysunitsCtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Force Ninja: make's exec of /bin/sh is denied by HMMAC on the
        # current OHOS device, breaking "Unix Makefiles" try-compiles.
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_CXX_STANDARD"] = 11
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.cache_variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: consumer executable was not run")
            return
        consumer = os.path.join(self.cpp.build.bindirs[0], "physunits_consumer")
        self.run(consumer, env="conanrun")
