#!/usr/bin/env python3
"""Conan test_package — libxau 1.0.11 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxauTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # X11/Xauth.h transitively includes <X11/Xfuncproto.h> from xorgproto.
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_libxau")
        self.run(test_bin, env="conanrun")