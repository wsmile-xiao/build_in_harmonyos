#!/usr/bin/env python3
"""Conan test_package — consumer verification for the powerstat CLI.

R34: the test must actually invoke the installed package binary with a
real command and check the observable result — not print a placeholder.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PowerstatTestConan(ConanFile):
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
        # Consumer: the installed binary must be runnable and report its version.
        # Use the runtime environment so the package bin/ is on PATH.
        self.run("powerstat -h >/dev/null 2>&1", env="conanrun")
        self.run("powerstat -h 2>&1 | grep -q 'version 0.04.06'", env="conanrun")
