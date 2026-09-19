#!/usr/bin/env python3
"""Conan consumer tests for SafeInt 3.0.28a."""
import platform

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SafeintTestConan(ConanFile):
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
        if platform.system() != "HarmonyOS":
            self.output.info(
                "Consumer runtime tests require native HarmonyOS; build passed"
            )
            return
        self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                self.build_folder
            ),
            env="conanrun",
        )
