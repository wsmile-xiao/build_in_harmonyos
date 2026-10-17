#!/usr/bin/env python3
"""Conan test_package — libxfixes 6.0.1 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxfixesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Xfixes.h transitively includes <X11/Xlib.h> (libx11) and
        # <X11/Xfuncproto.h> / <X11/extensions/xfixeswire.h> (xorgproto).
        # CMakeDeps only emits Target files for direct requirements, so both
        # must be required explicitly by the test consumer.
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libxfixes")
        self.run(test_bin, env="conanrun")
