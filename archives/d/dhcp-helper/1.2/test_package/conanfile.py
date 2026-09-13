#!/usr/bin/env python3
"""Conan test_package — dhcp-helper 1.2 CLI tool verification.

dhcp-helper is a privileged daemon (binds UDP 67/1067), so the test binary
receives the path of the installed `dhcp-helper` executable as argv[1] and
drives its privilege-free argument paths end-to-end (R34): version banner,
usage output, interface validation, and the missing-server guard.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DhcpHelperTestConan(ConanFile):
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
        helper_bin = os.path.join(
            self.dependencies["dhcp-helper"].package_folder, "sbin", "dhcp-helper"
        )
        test_bin = os.path.join(self.build_folder, "test_dhcp_helper")
        self.run(f'"{test_bin}" "{helper_bin}"', env="conanrun")
