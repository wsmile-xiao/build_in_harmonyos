#!/usr/bin/env python3
"""Consumer test for glaze 8.3.0."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class GlazeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

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
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The requested OHOS profile is native (build=host), so this path runs
        # on the device. Keep a concrete cross-build guard for other profiles.
        if cross_building(self):
            self.output.info("cross-building: consumer runtime test not executable")
            return
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_glaze")
        self.run('"%s"' % test_exe, env="conanrun")
