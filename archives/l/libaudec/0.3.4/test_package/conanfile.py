#!/usr/bin/env python3
"""Conan test_package for libaudec 0.3.4 (CMake consumer).

Real consumer contract on the OHOS device: the test program synthesizes a
16-bit PCM WAV, decodes it through the public libaudec API (identity read
plus a libsamplerate down-sample) and checks 12 assertions. Binary names
follow the repo convention (./test_package) so the device-run evidence is
unambiguous.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibaudecTestConan(ConanFile):
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
            # Linux-compatible compiler mode for this C consumer (boxfort
            # precedent).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = \
                "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def test(self):
        # Run the consumer only when the host can execute the binary; the
        # OHOS device profile is native here (can_run keeps non-native
        # cross builds from attempting an impossible execution).
        if can_run(self):
            self.run(
                os.path.join(self.build_folder, "test_package"),
                env="conanrun",
            )
