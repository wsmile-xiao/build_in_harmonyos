#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/sshfs/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SshfsTestConan(ConanFile):
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
        # Get the sshfs binary from the installed package and pass its absolute
        # path to the test (like bitwise), so --version does not depend on
        # PATH resolution inside the CI sandbox.
        dep = self.dependencies["sshfs"]
        sshfs_bin = os.path.join(dep.package_folder, "bin", "sshfs")
        test_bin = os.path.join(self.build_folder, "test_sshfs")
        self.run(f'{test_bin} "{sshfs_bin}"', env="conanrun")
