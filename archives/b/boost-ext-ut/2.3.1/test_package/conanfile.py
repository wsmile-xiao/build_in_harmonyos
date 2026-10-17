#!/usr/bin/env python3
"""Conan test_package for boost-ext-ut 2.3.1."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostExtUtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip consumer runtime test")
            return
        bindir = self.cpp.build.bindirs[0]
        # the consumer suite must pass (exit 0)
        self.run(os.path.join(bindir, "test_boost_ext_ut"), env="conanrun")
        # the failing-assertion probe must be reported as a failure (exit != 0):
        # proves the runner really evaluates expectations instead of always returning 0
        self.run(os.path.join(bindir, "test_boost_ext_ut_negative") + " && exit 1 || exit 0",
                 env="conanrun")
