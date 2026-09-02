#!/usr/bin/env python3
"""Conan consumer test for the cmock 2.7.0 Meson C library package."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout


class CMockTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = CMakeDeps, CMakeToolchain

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
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "cmock_consumer"),
            env="conanrun",
        )
