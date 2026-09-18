#!/usr/bin/env python3
"""test_package — libexecs 1.4 consumer probe."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building
from conan.tools.files import save


class LibexecsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "consumer_probe"), env="conanrun")
