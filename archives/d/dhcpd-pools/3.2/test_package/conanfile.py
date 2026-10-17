#!/usr/bin/env python3
"""Conan test_package - verify dhcpd-pools executable."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DhcpdPoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
            test_bin = os.path.join(self.build_folder, "test_dhcpd_pools")
            dhcpd_pools = os.path.join(
                self.dependencies["dhcpd-pools"].package_folder,
                "bin",
                "dhcpd-pools",
            )
            self.run(f'DHCPD_POOLS_PATH="{dhcpd_pools}" "{test_bin}"', env="conanrun")
