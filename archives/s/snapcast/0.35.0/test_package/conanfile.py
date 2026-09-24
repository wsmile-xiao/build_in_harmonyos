#!/usr/bin/env python3
"""Test package for snapcast — verifies snapserver and snapclient binaries."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SnapcastTestConan(ConanFile):
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
        # Get the snapcast package folder from dependencies
        snapcast_dep = self.dependencies["snapcast"]
        bin_dir = os.path.join(snapcast_dep.package_folder, "bin")
        snapserver = os.path.join(bin_dir, "snapserver")
        snapclient = os.path.join(bin_dir, "snapclient")

        self.run(f'"{snapserver}" --version', env="conanrun")
        self.run(f'"{snapclient}" --version', env="conanrun")
