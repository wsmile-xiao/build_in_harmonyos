#!/usr/bin/env python3
"""test_package for genann — consumer validation.

Simulates a business upper-layer component consuming genann through its
installed public header (genann.h) and public API only: init an ANN,
train it on XOR via backprop, and assert the feedforward result — a real
observable outcome of calling the exported API (not a print-only stub).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class GenannTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(
                self.settings.os
            )
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = (
                    "aarch64"
                )
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS profile is native (build=host), so this path runs on device.
        if cross_building(self):
            self.output.info("cross-building: consumer runtime test not executable")
            return
        test_exe = os.path.join(self.cpp.build.bindirs[0], "consumer_test")
        self.run('"%s"' % test_exe, env="conanrun")