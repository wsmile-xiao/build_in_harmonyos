#!/usr/bin/env python3
"""Conan test_package for lm-sensors 3.6.0.

Verifies that libsensors is linkable and its API is callable.
The test calls sensors_init(), iterates detected chips, and calls
sensors_cleanup(). On systems without hardware sensors, sensors_init()
returns non-zero but the API must still be callable (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LmSensorsTestConan(ConanFile):
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
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_lm_sensors")
        self.run(cmd, env="conanrun")
