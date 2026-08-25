#!/usr/bin/env python3
"""Conan test_package for autofs 5.1.9 — validates packaged artifacts."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class AutofsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_autofs")
        pkg_path = self.dependencies["autofs"].package_folder
        self.run("'%s' '%s'" % (bin_path, pkg_path), env="conanrun")