#!/usr/bin/env python3
"""Consumer and fault-injection tests for actor-framework 0.17.6."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ActorFrameworkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if not can_run(self):
            self.output.info(
                "Cross-built actor_probe; execute both scenarios on the "
                "HarmonyOS PC emulator."
            )
            return
        executable = os.path.join(self.cpp.build.bindir, "actor_probe")
        self.run(f'"{executable}"', env="conanrun")
        self.run(f'"{executable}" --expect-invalid', env="conanrun")
