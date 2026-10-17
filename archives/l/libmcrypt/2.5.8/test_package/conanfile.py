#!/usr/bin/env python3
"""Conan test_package for libmcrypt 2.5.8."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibmcryptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: test binary was built but not executed")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libmcrypt")
        self.run(f'"{exe}"', env="conanrun")
