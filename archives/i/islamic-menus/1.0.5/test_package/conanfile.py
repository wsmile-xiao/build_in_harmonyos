#!/usr/bin/env python3
"""Conan consumer test for islamic-menus package resources."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IslamicMenusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test_islamic_menus.c", "test_ohos.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # HarmonyOS is not in CMake's built-in platform table. Skip its
        # compiler ABI/works probes; build() still compiles this consumer.
        toolchain.cache_variables["CMAKE_C_COMPILER_FORCED"] = "ON"
        toolchain.variables["CMAKE_C_STANDARD"] = "99"
        toolchain.variables["CMAKE_C_STANDARD_REQUIRED"] = "ON"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Keep this tiny consumer build serial: the CI worker's automatic
        # -j20 setting exceeds its process limit.
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Target consumer was cross-compiled but cannot run on this build host"
            )
            return

        package = self.dependencies["islamic-menus"]
        consumer = os.path.abspath(os.path.join(
            self.build_folder, self.cpp.build.bindirs[0], "test_islamic_menus"
        ))
        script = os.path.join(self.recipe_folder, "test_ohos.sh")
        self.run(
            f'/system/bin/sh "{script}" "{consumer}" "{package.package_folder}"',
            env="conanrun",
        )
