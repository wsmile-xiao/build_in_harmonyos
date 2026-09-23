#!/usr/bin/env python3
"""Consumer test for the PBC 1.0.0 Conan package."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PbcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            toolchain.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            toolchain.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: consumer executable was compiled and linked")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_pbc")
        self.run(executable, env="conanrun")
