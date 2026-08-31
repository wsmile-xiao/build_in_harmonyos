#!/usr/bin/env python3
"""Test package for fish 3.7.1 — verifies the fish shell binary works."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FishTestConan(ConanFile):
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
        # Run fish --version to verify the binary works
        fish = self.dependencies["fish"]
        fish_bin = os.path.join(fish.package_folder, "bin", "fish")
        self.run(f"{fish_bin} --version", env="conanrun")
        # Verify fish_indent works
        fish_indent = os.path.join(fish.package_folder, "bin", "fish_indent")
        self.run(f"{fish_indent} --version", env="conanrun")
        # Run fish interactive command
        self.run(f'{fish_bin} -c "math 1+2"', env="conanrun")
