#!/usr/bin/env python3
"""Conan consumer test for Box2D 2.4.1."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Box2DTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        if cross_building(self):
            self.output.info("Cross-building: skip target executable run")
            return

        executable = "test_box2d.exe" if self.settings.os == "Windows" else "test_box2d"
        command = os.path.join(self.cpp.build.bindirs[0], executable)
        self.run(f'"{command}"', env="conanrun")
