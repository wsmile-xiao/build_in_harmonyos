#!/usr/bin/env python3
"""Conan test_package — range-v3 0.12.0

Consumer test: find_package(range-v3) + range-v3::range-v3 + verify basic ranges APIs.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RangeV3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "rangev3_test")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f'"{qemu}" "{bin_path}"', env="conanrun")
        else:
            self.run(bin_path, env="conanrun")
