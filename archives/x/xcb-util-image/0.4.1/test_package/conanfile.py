#!/usr/bin/env python3
"""Conan test_package — xcb-util-image 0.4.1 consumer link + API smoke test."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XcbUtilImageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CMakeDeps only generates include paths for directly-required
        # packages. libxcb headers (xcb/xcb.h, xcb/xproto.h) are needed
        # by the test source, so require it explicitly.
        self.requires("libxcb/1.17.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        test_bin = os.path.join(bindirs[0], "test_xcb_image")
        self.run(test_bin, env="conanrun")
