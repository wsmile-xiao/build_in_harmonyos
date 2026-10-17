#!/usr/bin/env python3
"""Conan test_package — libxdamage 1.1.6 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibxdamageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Xdamage.h transitively includes <X11/Xlib.h> (libx11),
        # <X11/extensions/Xfixes.h> (libxfixes) and
        # <X11/Xfuncproto.h> / <X11/extensions/damagewire.h> (xorgproto).
        # CMakeDeps only emits Target files for direct requirements, so all
        # must be required explicitly by the test consumer.
        # Dep chain aligned with the main recipe (cmd-pkgs track).
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")
        self.requires("libxfixes/6.1.0")
        self.requires("xorgproto/2025.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libxdamage")
        self.run(test_bin, env="conanrun")
