#!/usr/bin/env python3
"""Conan consumer test for openjpeg2 2.5.4."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class OpenJpeg2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        if str(self.settings.os) == "OHOS":
            self.conf.define("tools.build:jobs", 1)
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Runtime test unavailable; compile/link consumer check completed"
            )
            return

        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_openjpeg2",
        )
        self.run(executable, env="conanrun")
