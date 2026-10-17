#!/usr/bin/env python3
"""Conan test_package for libuio — verifies the library API and the lsuio CLI."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibuioTestConan(ConanFile):
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
        # R34: tests must actually exercise the package's API and binaries.
        # 1) library API: enumerate UIO devices + negative lookups
        cmake = CMake(self)
        cmake.test()

        # 2) CLI tool: lsuio --version goes through the getopt_long path
        #    (patch 0001) and must exit 0. Plain `lsuio` without UIO
        #    devices exits 1 upstream ("No UIO devices found"), so -V is
        #    the deterministic smoke command.
        dep = self.dependencies[self.tested_reference_str]
        lsuio = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "lsuio")
        self.run(f'"{lsuio}" --version', env="conanrun")
