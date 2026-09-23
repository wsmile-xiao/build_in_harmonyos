#!/usr/bin/env python3
"""Conan test package for gtk2 2.24.33."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class Gtk2TestConan(ConanFile):
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
            self.output.info("Runnable smoke skipped on this target")
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gtk2")
        self.run(f'"{bin_path}"', env="conanrun")
