#!/usr/bin/env python3
"""Conan test_package — xcb-util-keysyms 0.4.1 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XcbUtilKeysymsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps only generates include paths for directly-required
        # packages. xcb/xcb.h (from libxcb) is needed by the test source,
        # so require it explicitly.
        self.requires("libxcb/1.17.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_xcb-util-keysyms")
        self.run(test_bin, env="conanrun")