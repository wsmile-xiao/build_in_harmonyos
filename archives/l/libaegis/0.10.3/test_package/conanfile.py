#!/usr/bin/env python3
"""Conan test_package for libaegis/0.10.3."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibaegisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test.c", "kat_vectors.h"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Test code only needs C99; the pragma-targeted AES functions live
            # in the library, so no special arch flags are needed here either.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_aegis")
        self.run(test_bin, env="conanrun")
