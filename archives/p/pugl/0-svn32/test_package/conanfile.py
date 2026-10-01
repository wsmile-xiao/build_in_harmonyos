#!/usr/bin/env python3
"""Conan test package — Pugl public API and HarmonyOS backend."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PuglTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            api_test = os.path.join(self.cpp.build.bindir, "test_api")
            ohos_test = os.path.join(self.cpp.build.bindir, "test_ohos")
            self.run(api_test, env="conanrun")
            self.run(ohos_test, env="conanrun")
