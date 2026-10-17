#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test + HarmonyOS-specific test.

CI runs this automatically via `conan create` (which invokes test_package).
File location: archives/l/lockfree-queue/2cdf763421/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LockfreeQueueTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # HarmonyOS-specific test: run the binary directly (R02 evidence key)
        self.run(os.path.join(self.cpp.build.bindirs[0], "harmonyos_specific_test"), env="conanrun")
