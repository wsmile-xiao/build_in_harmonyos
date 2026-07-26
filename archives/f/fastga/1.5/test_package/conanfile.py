#!/usr/bin/env python3
"""Conan test_package for FASTGA 1.5."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FastgaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
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
        runner = os.path.join(self.cpp.build.bindirs[0], "test_fastga")
        fatogdb = os.path.join(
            self.dependencies["fastga"].package_folder, "bin", "FAtoGDB"
        )
        self.run('"{}" "{}"'.format(runner, fatogdb), env="conanrun")
