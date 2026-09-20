#!/usr/bin/env python3
"""Conan test_package for corepdf 1.0 — verifies the binary runs."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CorepdfTestConan(ConanFile):
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
        # R34: Execute the actual corepdf binary to verify it runs
        # Use offscreen platform for headless environment (no display)
        if can_run(self):
            self.run("QT_QPA_PLATFORM=offscreen corepdf --help", env="conanrun")
