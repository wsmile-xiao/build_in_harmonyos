#!/usr/bin/env python3
"""Consumer tests for libfakekey on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibfakekeyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test.c", "MANIFEST.yml"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_libfakekey"
        )
        self.run(executable, env="conanrun")
