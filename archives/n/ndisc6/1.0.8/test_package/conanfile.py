#!/usr/bin/env python3
"""Conan test_package — ndisc6 1.0.8

L1 test: verify the ndisc6 binary is installed and can show version.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Ndisc6TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Also verify the ndisc6 binary works
        pkg_folder = self.dependencies["ndisc6"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "ndisc6")
        if can_run(self):
            self.run(f'"{bin_path}" --version', env="conanrun")
