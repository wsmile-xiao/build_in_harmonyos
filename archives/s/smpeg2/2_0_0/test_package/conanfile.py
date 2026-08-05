#!/usr/bin/env python3
"""Conan test_package for smpeg2 2.0.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Smpeg2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _test_executable(self):
        suffix = ".exe" if self.settings.os == "Windows" else ""
        candidates = [
            os.path.join(self.build_folder, "test_smpeg2" + suffix),
            os.path.join(self.build_folder, str(self.settings.build_type), "test_smpeg2" + suffix),
            os.path.join(self.build_folder, "Debug", "test_smpeg2" + suffix),
            os.path.join(self.build_folder, "Release", "test_smpeg2" + suffix),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return candidates[0]

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = self._test_executable()
        if not os.path.isfile(bin_path):
            raise RuntimeError(f"Missing built test executable: {bin_path}")
        if can_run(self):
            self.run(f'"{bin_path}"', env="conanrun")
