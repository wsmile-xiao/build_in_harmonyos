#!/usr/bin/env python3
"""Conan consumer and fault-injection tests for plog 1.1.11."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PlogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "test_plog")
            self.run(executable, env="conanrun")
            self.run(f"{executable} --invalid-severity", env="conanrun")
        else:
            self.output.info(
                "Cross build: consumer test executable was built; "
                "run both scenarios on the HarmonyOS PC emulator."
            )
