#!/usr/bin/env python3
"""Conan consumer tests for SuperNOVAS."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SupernovasTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

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
            self.output.info("Cross-building: SuperNOVAS consumers compiled but cannot run")
            return

        bindir = self.cpp.build.bindir
        self.run(os.path.join(bindir, "test_supernovas_c"), env="conanrun")
        self.run(os.path.join(bindir, "test_supernovas_cpp"), env="conanrun")
