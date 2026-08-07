#!/usr/bin/env python3
"""Conan consumer test for libxc."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibxcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            ninja = shutil.which("ninja")
            if not ninja:
                raise ConanInvalidConfiguration(
                    "OHOS test_package requires ninja in PATH"
                )
            toolchain.generator = "Ninja"
            toolchain.variables["CMAKE_MAKE_PROGRAM"] = ninja
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libxc"), env="conanrun")
