#!/usr/bin/env python3
"""Conan test_package — libx11 1.8.13 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libx11TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Public headers transitively include <X11/Xfuncproto.h> from xorgproto.
        # CMakeDeps only generates Target files for directly-required packages,
        # so we have to require xorgproto/2025.1 explicitly in the test.
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_libx11")
        self.run(test_bin, env="conanrun")
