#!/usr/bin/env python3
"""Conan test_package — uhubctl 2.6.0 CLI tool verification.

uhubctl is a CLI tool, not a library, so the consumer test drives the
installed binary end-to-end (R34): it executes the packaged `uhubctl`
executable and asserts on real behavior — the -v version banner, the -h
usage text, and a graceful no-USB-hub listing run.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UhubctlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        uhubctl_bin = os.path.join(
            self.dependencies["uhubctl"].package_folder, "bin", "uhubctl"
        )
        test_bin = os.path.join(self.build_folder, "test_uhubctl")
        self.run(f'"{test_bin}" "{uhubctl_bin}"', env="conanrun")
