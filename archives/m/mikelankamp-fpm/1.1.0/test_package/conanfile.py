#!/usr/bin/env python3
"""test_package — builds and runs a real consumer of mikelankamp-fpm 1.1.0.

The consumer compiles against the *installed* headers only and asserts
observable results (exact fixed-point arithmetic, cross-format conversion,
sqrt/trig/rounding against the double reference, iostream insert/extract and
std::hash behaviour). It is the package's HarmonyOS-specific test row.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MikelankampFpmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            consumer = os.path.join(self.cpp.build.bindirs[0], "consumer")
            self.run(f'"{consumer}"', env="conanrun")
