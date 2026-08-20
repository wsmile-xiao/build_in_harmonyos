#!/usr/bin/env python3
"""Conan test package for entt 4.0.0 — header-only C++ ECS library."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EnttTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("Cross-building: skip consumer runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_entt"), env="conanrun")
