#!/usr/bin/env python3
"""Conan consumer test — rw 0.9 rank-width API and OHOS ABI checks."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            toolchain.cache_variables["RW_EXPECT_OHOS"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_rw")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the rw OHOS consumer tests"
                )
            self.run(f'"{qemu}" "{executable}"', env="conanrun")
        else:
            self.run(executable, env="conanrun")
