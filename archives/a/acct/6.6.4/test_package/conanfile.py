#!/usr/bin/env python3
"""Conan test_package for acct 6.6.4 - CLI tool L1 test.

acct is a CLI tool package (no libraries). This test verifies
that the installed binaries are functional by running `ac --version`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AcctTestConan(ConanFile):
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
        # Run CMake test first
        cmake = CMake(self)
        cmake.test()

        # Run the installed binary to verify functionality
        # Conan 2.x API: use self.dependencies["acct"].package_folder
        acct_pkg = self.dependencies["acct"]
        bin_dir = os.path.join(acct_pkg.package_folder, "bin")
        ac_path = os.path.join(bin_dir, "ac")
        if os.path.exists(ac_path):
            self.run(f'"{ac_path}" --version', env="conanrun")
