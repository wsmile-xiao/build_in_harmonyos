#!/usr/bin/env python3
"""Consumer test for the Mapbox Variant header-only package."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MapboxVariantTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Conan's OHOS setting is not a CMake system name.  Keep the target
        # architecture explicit while allowing the SDK toolchain/profile to
        # provide the compiler and sysroot details.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime execution after compile/link")
            return
        test_bin = os.path.join(self.build_folder, "bin", "test_package")
        self.run(test_bin, env="conanrun")
