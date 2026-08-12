#!/usr/bin/env python3
"""Conan test_package - verify ophcrack binary runs."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OphcrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        if can_run(self):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_ophcrack")
            ophcrack = os.path.join(self.dependencies["ophcrack"].package_folder, "bin", "ophcrack")
            self.run(f'OPHCRACK_PATH="{ophcrack}" "{test_bin}"', env="conanrun")
