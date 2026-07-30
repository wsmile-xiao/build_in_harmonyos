#!/usr/bin/env python3
"""Consumer and fault-injection tests for libkate 0.4.3."""

import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibkateTestConan(ConanFile):
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
        if self._can_run_target():
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_libkate"
            )
            self.run(executable, env="conanrun")
            self.run(
                f'"{executable}" --invalid-language',
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross build: libkate consumer was built; run normal and "
                "--invalid-language scenarios on the HarmonyOS PC emulator."
            )

    def _can_run_target(self):
        return str(self.settings.os) != "OHOS" and can_run(self)
