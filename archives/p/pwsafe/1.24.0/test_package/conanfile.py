#!/usr/bin/env python3
"""Conan test_package for pwsafe 1.24.0 — CLI tool smoke test.

Verifies the pwsafe-cli binary is functional by running it with
--help and checking it outputs supported arguments.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PwsafeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_pwsafe")
        self.run(cmd, env="conanrun")
