#!/usr/bin/env python3
"""Conan L1 consumer test for gperftools 2.17.2."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GperftoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
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
        executable = os.path.join(self.cpp.build.bindir, "test_gperftools")
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
