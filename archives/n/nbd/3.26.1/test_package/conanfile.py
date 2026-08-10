#!/usr/bin/env python3
"""Test package for nbd — verifies nbd-server binary runs."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NbdTestConan(ConanFile):
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
        # R34: test must substantively depend on the tested package.
        # nbd is a command-line tool; verify nbd-server runs and reports version.
        self.run("nbd-server --version", env="conanrun")
        # Also run the CMake-built test binary for link verification
        test_bin = os.path.join(self.build_folder, "test_nbd")
        self.run(test_bin, env="conanrun")
