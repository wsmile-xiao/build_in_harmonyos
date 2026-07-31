#!/usr/bin/env python3
"""Conan consumer test for EditorConfig Core C 0.12.9."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class EditorconfigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer linked but cannot run")
            return
        cmake = CMake(self)
        cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_editorconfig"),
            env="conanrun",
        )
