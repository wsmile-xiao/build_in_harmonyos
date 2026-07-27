#!/usr/bin/env python3
"""Conan test_package for c3c — C3 language compiler.

Verifies the installed compiler binary and its upstream internal test suite.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class C3CTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        if can_run(self):
            commands = (
                os.path.join(self.cpp.build.bindirs[0], "test_c3c"),
                "c3c --version",
                "c3c --help",
                "c3c utest",
            )
            for command in commands:
                if self.run(command, env="conanrun", ignore_errors=True) != 0:
                    raise ConanException(f"Test command failed: {command}")
