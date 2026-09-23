#!/usr/bin/env python3
"""Conan test_package — ddpt 0.97 CLI tool verification.

ddpt is a dd-style copy tool, so the test binary receives the path of the
installed `ddpt` executable as argv[1] and drives real copy jobs on regular
files (R34): version banner, deterministic file copy with byte comparison,
a /dev/zero fixed-count copy, and a missing-input failure path. None of
these need privileges or block devices.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DdptTestConan(ConanFile):
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
        ddpt_bin = os.path.join(
            self.dependencies["ddpt"].package_folder, "bin", "ddpt"
        )
        test_bin = os.path.join(self.build_folder, "test_ddpt")
        self.run(f'"{test_bin}" "{ddpt_bin}"', env="conanrun", cwd=self.build_folder)
