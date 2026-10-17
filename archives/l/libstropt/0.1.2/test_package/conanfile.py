#!/usr/bin/env python3
"""Conan consumer tests — libstropt 0.1.2."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibstroptTestConan(ConanFile):
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
        if not can_run(self):
            return
        bindir = self.cpp.build.bindir
        self.run(os.path.join(bindir, "test_libstropt"), env="conanrun")
        self.run(os.path.join(bindir, "test_libstropt_ohos"), env="conanrun")
