#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/gnucobol/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GnucobolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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

        dep = self.dependencies["gnucobol"]
        cobc = os.path.join(dep.package_folder, "bin", "cobc")
        cobcrun = os.path.join(dep.package_folder, "bin", "cobcrun")
        cobol_binary = os.path.join(self.build_folder, "conan-gnucobol-test")
        cobol_source = os.path.join(self.source_folder, "hello.cob")

        self.run(f'"{cobc}" --version', env="conanrun")
        self.run(f'"{cobcrun}" --version', env="conanrun")
        self.run(
            f'"{cobc}" -x -free -o "{cobol_binary}" "{cobol_source}"',
            env="conanrun",
        )
        self.run(f'"{cobol_binary}"', env="conanrun")
