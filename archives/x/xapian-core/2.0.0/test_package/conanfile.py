#!/usr/bin/env python3
"""Conan test_package for xapian-core 2.0.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XapianCoreTestConan(ConanFile):
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
        bin_name = "test_xapian_core.exe" if self.settings.os == "Windows" else "test_xapian_core"
        cmd = os.path.join(self.cpp.build.bindir, bin_name)
        self.run(cmd, env="conanrun")
