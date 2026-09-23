#!/usr/bin/env python3
"""Conan consumer test for open62541 1.5.6."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Open62541TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
            self.output.info(
                "cross-building: compile and link verified; runtime execution skipped"
            )
            return
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_open62541")
        self.run(test_binary, env="conanrun")
