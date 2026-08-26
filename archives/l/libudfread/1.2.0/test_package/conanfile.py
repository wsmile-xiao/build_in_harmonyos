#!/usr/bin/env python3
"""Consumer and fault-injection tests for libudfread 1.2.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibudfreadTestConan(ConanFile):
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
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_libudfread"
            )
            self.run(executable, env="conanrun")
            self.run(
                f'"{executable}" --missing-path',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: libudfread consumer was built; run normal and "
                "--missing-path scenarios on the HarmonyOS PC emulator."
            )
