#!/usr/bin/env python3
"""Consumer test for mathfu 1.1.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MathfuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "11"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        if self.settings.os in ("Linux", "OHOS"):
            # Keep CMake's platform logic usable with the OHOS Conan profile.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # The OHOS SDK libc++.so is a linker script (INPUT(-lc++_shared))
            # that the runtime loader cannot resolve, so the consumer test
            # binary is linked statically to run natively on the target
            # (same approach as the recipe's upstream test binaries).
            tc.cache_variables["MATHFU_TEST_LINK_STATIC"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            executable = os.path.join(
                self.cpp.build.bindirs[0], "mathfu_test"
            )
            self.run(executable, env="conanrun")
