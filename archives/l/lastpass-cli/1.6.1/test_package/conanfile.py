#!/usr/bin/env python3
"""Conan test_package for lastpass-cli — verifies lpass binary works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LastpassCliTestConan(ConanFile):
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
        # R34: Test actually runs the lpass binary via the test executable
        bin_path = os.path.join(self.dependencies["lastpass-cli"].package_folder, "bin", "lpass")
        # Set LPASS_PATH for the test binary
        os.environ["LPASS_PATH"] = bin_path
        self.run("./test_lastpass_cli", env=["conanrun"])
        # Also verify directly
        self.run(f'"{bin_path}" --version', env=["conanrun"])
