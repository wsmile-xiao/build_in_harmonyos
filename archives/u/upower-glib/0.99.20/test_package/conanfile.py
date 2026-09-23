#!/usr/bin/env python3
"""Conan consumer test for upower-glib 0.99.20 (HarmonyOS PC)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class UpowerGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.88.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_upower-glib")
        self.run(binary, env="conanrun")
        ohos_binary = os.path.join(self.cpp.build.bindirs[0], "test_ohos")
        self.run(ohos_binary, env="conanrun")
