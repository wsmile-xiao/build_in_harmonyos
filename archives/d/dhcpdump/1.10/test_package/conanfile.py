#!/usr/bin/env python3
"""Conan test_package - verify dhcpdump binary runs."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DhcpdumpTestConan(ConanFile):
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
            test_bin = os.path.join(self.build_folder, "test_dhcpdump")
            dhcpdump = os.path.join(self.dependencies["dhcpdump"].package_folder, "bin", "dhcpdump")
            self.run(f'DHCPDUMP_PATH="{dhcpdump}" "{test_bin}"', env="conanrun")