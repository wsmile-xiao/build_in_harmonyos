#!/usr/bin/env python3
"""Consumer test for sparse-map/0.7.0."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SparseMapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "sparse_map_consumer")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the cross-compiled test package"
                )
            self.run(f'"{qemu}" "{binary}"', env="conanrun")
        else:
            self.run(binary, env="conanrun")
