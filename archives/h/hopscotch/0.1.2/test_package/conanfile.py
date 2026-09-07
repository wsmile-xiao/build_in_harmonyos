#!/usr/bin/env python3
"""Conan test package for hopscotch 0.1.2 (CMake API consumer)."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class HopscotchTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = ()

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The installed CMake has no HarmonyOS platform module; use its
            # Linux-compatible compiler mode for this C consumer.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def test(self):
        # Run the consumer only when the host binary is executable. The
        # OHOS device profile is native here; can_run keeps cross builds
        # from attempting to execute an incompatible binary.
        if can_run(self):
            self.run(
                os.path.join(self.build_folder, "test_package"),
                env="conanrun",
            )
