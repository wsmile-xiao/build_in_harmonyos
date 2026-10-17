#!/usr/bin/env python3
"""Conan test_package — snaphu 2.0.7 CLI verification (R34).

snaphu is a CLI application, so there is no library to link against. This
test builds a small C driver that receives the path of the installed
`snaphu` executable and drives it end-to-end: the version banner, a
known-answer unwrap of an all-zero phase grid, and a wrapped-ramp unwrap
with artifact-size / finiteness / non-degeneracy assertions.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SnaphuTestConan(ConanFile):
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
        snaphu_bin = os.path.join(
            self.dependencies["snaphu"].package_folder, "bin", "snaphu"
        )
        test_bin = os.path.join(self.build_folder, "test_snaphu")
        self.run(f'"{test_bin}" "{snaphu_bin}"', env="conanrun")
