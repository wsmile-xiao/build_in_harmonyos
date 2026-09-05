#!/usr/bin/env python3
"""Consumer test for string_id 2.0-3."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class StringIdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_package"),
                env="conanrun",
            )
        else:
            self.output.info("Cross-building: consumer runtime test skipped")
