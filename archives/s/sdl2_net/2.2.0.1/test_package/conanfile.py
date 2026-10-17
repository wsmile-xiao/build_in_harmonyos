#!/usr/bin/env python3
"""Conan consumer tests for SDL2_net 2.2.0.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Sdl2NetTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tested = self.dependencies["sdl2_net"]
        sdl2 = self.dependencies["sdl2"]
        tc.variables["SDL2_NET_TEST_SHARED"] = bool(
            tested.options.get_safe("shared", False)
        )
        tc.variables["EXPECTED_SDL2_ROOT"] = sdl2.package_folder.replace(
            "\\", "/"
        )
        tc.variables["EXPECTED_SDL2_NET_ROOT"] = tested.package_folder.replace(
            "\\", "/"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "NOT_RUN SDL2_NET_CONSUMER_TESTS=0/7 reason=cross_building"
            )
            return
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env="conanrun",
        )
