#!/usr/bin/env python3
"""Conan consumer test for nng 1.10.1 using CMake."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NngTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        dependency = self.dependencies["nng"]
        nngcat = os.path.join(
            dependency.package_folder,
            dependency.cpp_info.bindirs[0],
            "nngcat",
        )
        self.run(f'"{nngcat}" --version', env="conanrun")
